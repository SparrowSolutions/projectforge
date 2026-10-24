export const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export async function apiRequest(path:string, token:string, opts:RequestInit={}) {
  const res=await fetch(API+path,{...opts,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`} : {}),...(opts.headers||{})}});
  if(!res.ok){const body=await res.json().catch(()=>({}));throw new Error(body.detail||`Request failed (${res.status})`)}
  if(res.status===204)return null;
  return res.json();
}
