export function rotatedSize(width,height,degrees){
  const angle=((degrees%360)+360)%360;
  if(angle===0||angle===180)return {width,height};
  if(angle===90||angle===270)return {width:height,height:width};
  const radians=angle*Math.PI/180,c=Math.abs(Math.cos(radians)),s=Math.abs(Math.sin(radians));
  return {width:Math.ceil(width*c+height*s),height:Math.ceil(width*s+height*c)};
}
export function fitRect(width,height,viewWidth,viewHeight,zoom=1,pan={x:0,y:0}){
  const scale=Math.max(0,Math.min((viewWidth-24)/width,(viewHeight-24)/height))*zoom;
  return {x:(viewWidth-width*scale)/2+pan.x,y:(viewHeight-height*scale)/2+pan.y,width:width*scale,height:height*scale,scale};
}
export function sourcePoint(point,rect,width,height){
  return {x:Math.max(0,Math.min(width,(point.x-rect.x)/rect.scale)),y:Math.max(0,Math.min(height,(point.y-rect.y)/rect.scale))};
}
export function selectionBounds(points,width,height){
  if(points.length<2)return {x:0,y:0,w:width,h:height};
  const xs=points.map(p=>p.x),ys=points.map(p=>p.y);
  const x=Math.max(0,Math.floor(Math.min(...xs))),y=Math.max(0,Math.floor(Math.min(...ys)));
  return {x,y,w:Math.min(width,Math.ceil(Math.max(...xs)))-x,h:Math.min(height,Math.ceil(Math.max(...ys)))-y};
}
export function rotatedCorners(width,height,degrees,rect){
  const a=degrees*Math.PI/180,c=Math.cos(a),s=Math.sin(a),cx=rect.x+rect.width/2,cy=rect.y+rect.height/2;
  return [[-width/2,-height/2],[width/2,-height/2],[width/2,height/2],[-width/2,height/2]].map(([x,y])=>({
    x:cx+(x*c-y*s)*rect.scale,y:cy+(x*s+y*c)*rect.scale
  }));
}
export function dragRotation(initialAngle,initialBearing,currentBearing,snap=false){
  const delta=((currentBearing-initialBearing+540)%360)-180;
  let angle=initialAngle+delta;if(snap)angle=Math.round(angle/15)*15;
  return Math.round((((angle+540)%360)-180)*10)/10;
}
