import assert from "node:assert/strict";
import {fitRect,rotatedSize,sourcePoint,selectionBounds} from "../browser-extension/geometry.js";
for(const [width,height] of [[1024,1024],[1600,900],[900,1600],[40,80]]){
  for(const [vw,vh] of [[900,660],[1400,480],[420,760]]){
    const r=fitRect(width,height,vw,vh);
    assert.ok(Math.abs(r.width/r.height-width/height)<1e-10,"Aspect ratio must remain unchanged");
    assert.ok(r.width<=vw&&r.height<=vh);
    const center=sourcePoint({x:r.x+r.width/2,y:r.y+r.height/2},r,width,height);
    assert.ok(Math.abs(center.x-width/2)<1e-7); assert.ok(Math.abs(center.y-height/2)<1e-7);
  }
}
assert.deepEqual(rotatedSize(400,200,90),{width:200,height:400});
assert.deepEqual(rotatedSize(400,200,-90),{width:200,height:400});
assert.deepEqual(rotatedSize(400,200,0),{width:400,height:200});
assert.deepEqual(selectionBounds([{x:20.4,y:10.2},{x:200.8,y:90.1}],400,200),{x:20,y:10,w:181,h:81});
console.log("Extension geometry passed: 4 aspect ratios × 3 viewports, rotation, ROI coordinates.");
