/* Local browser integration QA with a fake Chrome bridge; no remote websites or AI. */
const fs=require("node:fs"),path=require("node:path"),http=require("node:http"),assert=require("node:assert/strict");
let playwright;
try{playwright=require("playwright");}catch{
  playwright=require(process.env.PLAYWRIGHT_MODULE||path.join(process.env.USERPROFILE,".cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright"));
}
const root=path.resolve(__dirname,".."),version=JSON.parse(fs.readFileSync(path.join(root,"browser-extension","manifest.json"),"utf8")).version;
const output=path.join(root,"test-output","extension-v"+version);fs.mkdirSync(output,{recursive:true});
const server=http.createServer((req,res)=>{
  const url=new URL(req.url,"http://localhost"),target=path.resolve(root,"."+decodeURIComponent(url.pathname));
  if(!target.startsWith(root+path.sep)){res.writeHead(403).end();return;}
  fs.readFile(target,(error,data)=>{
    if(error){res.writeHead(404).end();return;}
    const type={".js":"text/javascript",".html":"text/html",".css":"text/css",".svg":"image/svg+xml",".png":"image/png"}[path.extname(target)]||"application/octet-stream";
    res.writeHead(200,{"Content-Type":type});res.end(data);
  });
});
(async()=>{
  await new Promise(resolve=>server.listen(0,"127.0.0.1",resolve));
  const origin="http://127.0.0.1:"+server.address().port;
  const browser=await playwright.chromium.launch({channel:"msedge",headless:true});
  try{
    const context=await browser.newContext({viewport:{width:1280,height:800},deviceScaleFactor:1.5});
    const page=await context.newPage();const errors=[];page.on("pageerror",error=>errors.push(error.message));
    await page.addInitScript(({origin})=>{
      const source=document.createElement("canvas");source.width=400;source.height=200;const p=source.getContext("2d");
      p.fillStyle="red";p.fillRect(0,0,200,200);p.fillStyle="#00ff00";p.fillRect(200,0,200,200);
      window.fixtureURL=source.toDataURL("image/png");window.bridgeMessages=[];
      window.chrome={permissions:{request:async()=>true},storage:{local:{get:async id=>({[id]:{page:"https://example.invalid/private/listing?tracking=secret",images:Array.from({length:30},(_,i)=>({url:window.fixtureURL,alt:"Fixture "+(i+1)}))}})}},
        runtime:{sendNativeMessage:async(name,payload)=>{window.bridgeMessages.push(payload);return {ok:true,message:"Đã nhận ảnh đã xoay."};}}};
    },{origin});
    await page.goto(origin+"/browser-extension/selector.html?id=fixture");
    await page.locator(".candidate").first().dblclick();
    await page.waitForFunction(()=>!document.getElementById("send").disabled);
    assert.equal(await page.locator("#placeholder").isVisible(),false);
    assert.equal(await page.locator("#page").count(),0);
    const toolbar=await page.locator(".toolbar").boundingBox();
    await page.locator("#images").evaluate(el=>el.scrollTop=600);
    const toolbarAfter=await page.locator(".toolbar").boundingBox();assert.equal(toolbar.y,toolbarAfter.y);
    const canvas=await page.locator("#canvas").evaluate(el=>({width:el.width,height:el.height,rect:el.getBoundingClientRect().toJSON()}));
    assert.ok(Math.abs(canvas.width/canvas.height-canvas.rect.width/canvas.rect.height)<.005);
    await page.screenshot({path:path.join(output,"1280x800.png")});
    await page.locator("#zoomOut").click();
    const anchor=await page.evaluate(async()=>{
      const {fitRect,rotatedCorners}=await import("/browser-extension/geometry.js");
      const box=document.getElementById("canvas").getBoundingClientRect(),r=fitRect(400,200,box.width,box.height,1/1.2);
      const p=rotatedCorners(400,200,0,r)[1],center={x:r.x+r.width/2,y:r.y+r.height/2};
      const x=p.x-center.x,y=p.y-center.y,a=28*Math.PI/180;
      return {start:{x:box.left+p.x,y:box.top+p.y},end:{x:box.left+center.x+x*Math.cos(a)-y*Math.sin(a),y:box.top+center.y+x*Math.sin(a)+y*Math.cos(a)}};
    });
    await page.mouse.move(anchor.start.x,anchor.start.y);await page.mouse.down();await page.keyboard.down("Shift");
    await page.mouse.move(anchor.end.x,anchor.end.y,{steps:8});await page.mouse.up();await page.keyboard.up("Shift");
    assert.equal(Number(await page.locator("#angle").inputValue()),30);
    await page.screenshot({path:path.join(output,"corner-rotation.png")});
    await page.locator("#resetAngle").click();
    await page.locator("#rotateRight").click();await page.locator("#send").click();
    await page.waitForFunction(()=>window.bridgeMessages.length===1);
    const pixels=await page.evaluate(async()=>{
      const payload=window.bridgeMessages[0],im=await createImageBitmap(await (await fetch("data:image/png;base64,"+payload.image)).blob());
      const result=document.createElement("canvas");result.width=im.width;result.height=im.height;const p=result.getContext("2d");p.drawImage(im,0,0);
      return {width:im.width,height:im.height,angle:payload.source_rotation_degrees,top:Array.from(p.getImageData(100,100,1,1).data),bottom:Array.from(p.getImageData(100,300,1,1).data)};
    });
    assert.deepEqual(pixels,{width:200,height:400,angle:90,top:[255,0,0,255],bottom:[0,255,0,255]});
    await page.setViewportSize({width:1920,height:1080});await page.screenshot({path:path.join(output,"1920x1080.png")});
    const theme=await page.locator("#send").evaluate(el=>({background:getComputedStyle(el).backgroundColor,scheme:getComputedStyle(document.documentElement).colorScheme}));
    assert.equal(theme.background,"rgb(31, 107, 58)");assert.equal(theme.scheme,"light");
    assert.deepEqual(errors,[]);console.log(JSON.stringify({double_click_load:true,toolbar_fixed:true,aspect_ratio:true,corner_drag_and_shift_snap:true,rotated_pixels:true,forest_light_theme:true,browser_errors:errors}));
    await context.close();
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;}).finally(()=>server.close());
