import {CircleHelp} from 'lucide-react';
export default function EmptyState({text}:{text:string}){return <div className="empty-state"><span><CircleHelp size={22}/></span><p>{text}</p></div>}
