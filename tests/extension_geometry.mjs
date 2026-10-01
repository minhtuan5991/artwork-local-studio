import assert from "node:assert/strict";
import {fitRect,rotatedSize,sourcePoint,selectionBounds,rotatedCorners,dragRotation} from "../browser-extension/geometry.js";
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
const corners=rotatedCorners(400,200,0,fitRect(400,200,800,600));
assert.equal(corners.length,4);assert.ok(corners[1].x>corners[0].x&&corners[1].y===corners[0].y);
assert.equal(dragRotation(0,-45,45),90);assert.equal(dragRotation(10,175,-175),20);
assert.equal(dragRotation(0,-45,-16,true),30);assert.equal(dragRotation(0,45,14,true),-30);
console.log("Extension geometry passed: 4 aspect ratios × 3 viewports, rotation, ROI coordinates.");
