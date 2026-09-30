chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({id:"artwork-image",title:"Artwork Local Studio — chọn artwork",contexts:["image"]});
  chrome.contextMenus.create({id:"artwork-page",title:"Artwork Local Studio — ảnh trên trang",contexts:["page"]});
});

async function openSelector(tab,src) {
  let images=[];
  try {
    const result=await chrome.scripting.executeScript({
      target:{tabId:tab.id},
      func:()=>Array.from(document.images).filter(im=>im.naturalWidth>=100&&im.naturalHeight>=100)
        .map(im=>({url:im.currentSrc||im.src,width:im.naturalWidth,height:im.naturalHeight,alt:im.alt.slice(0,120)})).slice(0,120)
    });
    images=result[0]?.result||[];
  } catch { /* Context image remains usable when a page forbids injection. */ }
  if(src) images.unshift({url:src,alt:"Ảnh đã chọn"});
  const seen=new Set(); images=images.filter(im=>{if(seen.has(im.url))return false;seen.add(im.url);return true;});
  const id=crypto.randomUUID();
  await chrome.storage.local.set({[id]:{images,page:tab.url||"",created:Date.now()}});
  await chrome.tabs.create({url:chrome.runtime.getURL("selector.html")+"?id="+id});
  const all=await chrome.storage.local.get(null);
  const stale=Object.entries(all).filter(([,value])=>value.created&&Date.now()-value.created>86400000).map(([key])=>key);
  if(stale.length) await chrome.storage.local.remove(stale);
}
chrome.contextMenus.onClicked.addListener((info,tab)=> {
  if(info.menuItemId==="artwork-image"||info.menuItemId==="artwork-page")
    openSelector(tab,info.srcUrl).catch(console.error);
});
chrome.action.onClicked.addListener(tab=>openSelector(tab).catch(console.error));
