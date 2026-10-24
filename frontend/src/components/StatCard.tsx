import type {ReactNode} from 'react';
import {MoreHorizontal} from 'lucide-react';
export default function StatCard({icon,label,value,foot,tone}:{icon:ReactNode;label:string;value:any;foot:string;tone:string}){return <div className="stat-card"><div className="stat-top"><span className={`stat-icon ${tone}`}>{icon}</span><span className="stat-kebab"><MoreHorizontal size={17}/></span></div><div className="stat-label">{label}</div><div className="stat-value">{value}</div><div className="stat-foot">{foot}</div></div>}
