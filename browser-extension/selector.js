import {rotatedSize,fitRect,sourcePoint,selectionBounds} from "./geometry.js";
const $=id=>document.getElementById(id),canvas=$("canvas"),ctx=canvas.getContext("2d");
let image=null,sourceUrl="",pageUrl="",angle=0,zoom=1,pan={x:0,y:0},points=[],drag=false,panning=false,last={x:0,y:0};
let view={width:1,height:1,dpr:1},loadSequence=0,controller=null,sending=false;
function status(message,error=false){$("status").textContent=message;$("status").classList.toggle("error",error);}
function dimensions(){return image?rotatedSize(image.width,image.height,angle):{width:1,height:1};}
function displayRect(){const d=dimensions();return fitRect(d.width,d.height,view.width,view.height,zoom,pan);}
function position(event){const rect=canvas.getBoundingClientRect();return {x:event.clientX-rect.left,y:event.clientY-rect.top};}
function original(point){const d=dimensions();return sourcePoint(point,displayRect(),d.width,d.height);}
function resizeCanvas(){
  const bounds=$("viewport").getBoundingClientRect();view={width:Math.max(1,bounds.width),height:Math.max(1,bounds.height),dpr:window.devicePixelRatio||1};
  canvas.width=Math.round(view.width*view.dpr);canvas.height=Math.round(view.height*view.dpr);draw();
}
function draw(){
  ctx.setTransform(view.dpr,0,0,view.dpr,0,0);ctx.clearRect(0,0,view.width,view.height);
  ctx.fillStyle="#f4f5f9";ctx.fillRect(0,0,view.width,view.height);ctx.fillStyle="#e5e7ee";
  for(let y=0;y<view.height;y+=16)for(let x=0;x<view.width;x+=16)if((x/16+y/16)%2)ctx.fillRect(x,y,16,16);
  if(!image)return;
  const r=displayRect(),d=dimensions();
  ctx.save();ctx.translate(r.x+d.width*r.scale/2,r.y+d.height*r.scale/2);ctx.scale(r.scale,r.scale);
  ctx.rotate(angle*Math.PI/180);ctx.drawImage(image,-image.width/2,-image.height/2);ctx.restore();
  if(angle){ctx.beginPath();for(const f of [1/3,2/3]){ctx.moveTo(view.width*f,0);ctx.lineTo(view.width*f,view.height);ctx.moveTo(0,view.height*f);ctx.lineTo(view.width,view.height*f);}ctx.strokeStyle="rgba(255,255,255,.35)";ctx.lineWidth=1;ctx.stroke();}
  if(points.length<2)return;
  ctx.beginPath();
  if($("mode").value==="rectangle"){const [a,b]=points;ctx.rect(r.x+a.x*r.scale,r.y+a.y*r.scale,(b.x-a.x)*r.scale,(b.y-a.y)*r.scale);}
  else{points.forEach((p,i)=>ctx[i?"lineTo":"moveTo"](r.x+p.x*r.scale,r.y+p.y*r.scale));ctx.closePath();}
  ctx.fillStyle="rgba(109,74,255,.12)";ctx.fill();ctx.strokeStyle="#8e76ff";ctx.lineWidth=2;ctx.stroke();
}
function setAngle(value){
  if(sending)return;
  if(!Number.isFinite(value)||value<-180||value>180){status("Góc xoay phải từ −180° đến 180°.",true);return;}
  angle=value;$("angle").value=angle;points=[];zoom=1;pan={x:0,y:0};draw();
  if(image)status("Nguồn đã xoay "+angle+"° · Khoanh lại vùng artwork trên ảnh đã xoay.");
}
$("angle").addEventListener("change",()=>setAngle(Number($("angle").value)));
$("rotateLeft").onclick=()=>setAngle((angle-90+540)%360-180);
$("rotateRight").onclick=()=>setAngle((angle+90+540)%360-180);
$("resetAngle").onclick=()=>setAngle(0);
canvas.addEventListener("pointerdown",e=>{
  if(!image||sending)return;last=position(e);panning=e.altKey||e.button===1;
  if(!panning&&e.button===0&&$("mode").value!=="view"){drag=true;const p=original(last);points=$("mode").value==="rectangle"?[p,p]:[p];}
  canvas.setPointerCapture(e.pointerId);draw();
});
canvas.addEventListener("pointermove",e=>{
  if(!image||sending)return;const p=position(e);
  if(panning){pan.x+=p.x-last.x;pan.y+=p.y-last.y;last=p;}
  else if(drag){if($("mode").value==="rectangle")points[1]=original(p);else if(points.length<10000)points.push(original(p));}draw();
});
for(const event of ["pointerup","pointercancel"])canvas.addEventListener(event,()=>{drag=false;panning=false;});
canvas.addEventListener("wheel",e=>{e.preventDefault();zoom=Math.max(.5,Math.min(8,zoom*(e.deltaY<0?1.15:1/1.15)));draw();},{passive:false});
$("mode").addEventListener("change",()=>{points=[];draw();});
$("clear").onclick=()=>{points=[];draw();};
$("reset").onclick=()=>{zoom=1;pan={x:0,y:0};draw();};
$("zoomIn").onclick=()=>{zoom=Math.min(8,zoom*1.2);draw();};
$("zoomOut").onclick=()=>{zoom=Math.max(.5,zoom/1.2);draw();};
async function loadImage(url){
  if(sending)return;
  const sequence=++loadSequence;
  try{
    const parsed=new URL(url);
    if(!["https:","http:","data:"].includes(parsed.protocol))throw Error("Ảnh blob không tải trực tiếp được. Dùng Copy image rồi Ctrl+V trong app.");
    if(parsed.protocol!=="data:"&&!await chrome.permissions.request({origins:[parsed.origin+"/*"]}))throw Error("Chưa có quyền tải ảnh.");
    if(sequence!==loadSequence)return;
    controller?.abort();controller=new AbortController();$("load").disabled=true;$("send").disabled=true;status("Đang tải ảnh…");
    const response=await fetch(url,{credentials:"omit",signal:controller.signal});
    if(!response.ok)throw Error("Website từ chối tải ảnh. Dùng Copy image rồi Ctrl+V trong app.");
    const declared=Number(response.headers.get("Content-Length"));if(declared>25*1024*1024)throw Error("Ảnh vượt 25 MB.");
    const blob=await response.blob();if(blob.size>25*1024*1024)throw Error("Ảnh vượt 25 MB.");
    const bitmap=await createImageBitmap(blob);
    if(bitmap.width*bitmap.height>40000000||Math.min(bitmap.width,bitmap.height)<16){bitmap.close();throw Error("Kích thước ảnh không hợp lệ.");}
    if(sequence!==loadSequence){bitmap.close();return;}
    image?.close();image=bitmap;sourceUrl=url;angle=0;$("angle").value=0;zoom=1;pan={x:0,y:0};points=[];
    $("placeholder").hidden=true;draw();status(image.width+" × "+image.height+" · Xoay thẳng, khoanh vùng rồi gửi vào Queue.");
  }catch(error){if(sequence===loadSequence&&error.name!=="AbortError")status(error.message,true);}
  finally{if(sequence===loadSequence){$("load").disabled=false;$("send").disabled=!image||sending;}}
}
$("load").onclick=()=>loadImage($("url").value.trim());
$("send").onclick=async()=>{
  if(!image||sending)return;
  try{
    const d=dimensions();
    if($("mode").value==="lasso"&&points.length>0&&points.length<3)throw Error("Lasso cần ít nhất ba điểm.");
    const bounds=selectionBounds(points,d.width,d.height);
    if(Math.min(bounds.w,bounds.h)<16)throw Error("Vùng chọn cần ít nhất 16 pixel mỗi chiều.");
    if(bounds.w*bounds.h>40000000)throw Error("Ảnh sau xoay vượt 40 megapixel. Chọn vùng artwork nhỏ hơn.");
    const output=document.createElement("canvas");output.width=bounds.w;output.height=bounds.h;const paint=output.getContext("2d");
    if(points.length>=3&&$("mode").value==="lasso"){paint.beginPath();points.forEach((p,i)=>paint[i?"lineTo":"moveTo"](p.x-bounds.x,p.y-bounds.y));paint.closePath();paint.clip();}
    paint.translate(d.width/2-bounds.x,d.height/2-bounds.y);paint.rotate(angle*Math.PI/180);paint.drawImage(image,-image.width/2,-image.height/2);
    const base64=output.toDataURL("image/png").split(",")[1];
    if(base64.length>25*1024*1024*4/3)throw Error("PNG sau crop vượt 25 MB. Chọn vùng nhỏ hơn.");
    sending=true;$("send").disabled=true;$("load").disabled=true;status("Đang chuyển ảnh đã xoay vào app…");
    const reply=await chrome.runtime.sendNativeMessage("com.artworklocal.studio",{action:"enqueue",image:base64,name:"web-artwork.png",source_url:sourceUrl,source_page:pageUrl,
      source_rotation_degrees:angle,options:{size:Number($("size").value),background:$("background").value,chroma:$("chroma").value,detail:$("detail").value}});
    if(!reply.ok)throw Error(reply.error||"App chưa nhận ảnh.");status(reply.message);
  }catch(error){status(error.message+" Kết nối: mở app → Cài đặt → Ảnh website → Đăng ký kết nối.",true);}
  finally{sending=false;$("send").disabled=!image;$("load").disabled=false;}
};
async function init(){
  const id=new URLSearchParams(location.search).get("id");
  if(!id){status("Chuột phải ảnh trên website để mở thư viện.",true);return;}
  const saved=(await chrome.storage.local.get(id))[id];
  if(!saved){status("Không còn dữ liệu ảnh. Chuột phải ảnh trên website và mở lại.",true);return;}
  pageUrl=saved.page;$("imageCount").textContent=saved.images.length;
  for(const candidate of saved.images){
    const element=document.createElement("button");element.className="candidate";element.title=candidate.alt||"Ảnh nguồn";element.setAttribute("aria-label",(candidate.alt||"Ảnh nguồn")+". Click đúp để tải.");
    const thumbnail=document.createElement("img");thumbnail.src=candidate.url;thumbnail.alt=candidate.alt||"Ảnh nguồn";thumbnail.referrerPolicy="no-referrer";thumbnail.loading="lazy";element.appendChild(thumbnail);
    function select(){document.querySelectorAll(".candidate").forEach(el=>el.classList.remove("selected"));element.classList.add("selected");$("url").value=candidate.url;}
    element.onclick=()=>{select();status("Click đúp để tải ảnh, hoặc bấm Tải ảnh đã chọn.");};
    element.ondblclick=()=>{if(sending)return;select();loadImage(candidate.url);};
    element.addEventListener("keydown",event=>{if(event.key==="Enter"&&!sending){event.preventDefault();select();loadImage(candidate.url);}});
    $("images").appendChild(element);
  }
  if(saved.images.length){$("url").value=saved.images[0].url;$("images").firstChild.classList.add("selected");}
}
new ResizeObserver(resizeCanvas).observe($("viewport"));window.addEventListener("resize",resizeCanvas);
init().catch(error=>status(error.message,true));
