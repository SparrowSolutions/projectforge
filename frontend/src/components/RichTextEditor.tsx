import {useEffect} from 'react';
import {EditorContent,useEditor} from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Link from '@tiptap/extension-link';
import Underline from '@tiptap/extension-underline';
import {Bold,Italic,Underline as UnderlineIcon,Strikethrough,Heading1,Heading2,List,ListOrdered,Quote,Code,Link as LinkIcon,Undo2,Redo2,Minus} from 'lucide-react';
import './RichTextEditor.css';

type Props={value:string;onChange:(html:string)=>void;placeholder?:string;minHeight?:number};
export default function RichTextEditor({value,onChange,placeholder='Write something…',minHeight=220}:Props){
 const editor=useEditor({extensions:[StarterKit.configure({link:false}),Underline,Link.configure({openOnClick:false,autolink:true,HTMLAttributes:{rel:'noopener noreferrer nofollow',target:'_blank'}})],content:value||'',editorProps:{attributes:{class:'wysiwyg-content','data-placeholder':placeholder}},onUpdate:({editor})=>onChange(editor.getHTML())});
 useEffect(()=>{if(editor&&value!==editor.getHTML())editor.commands.setContent(value||'',{emitUpdate:false})},[value,editor]);
 if(!editor)return null;
 const cmd=(label:string,active:boolean,run:()=>void,icon:React.ReactNode)=><button type="button" title={label} aria-label={label} className={`wysiwyg-tool ${active?'is-active':''}`} onClick={run}>{icon}</button>;
 const addLink=()=>{const previous=editor.getAttributes('link').href as string|undefined;const url=window.prompt('Enter URL',previous||'https://');if(url===null)return;if(!url.trim()){editor.chain().focus().unsetLink().run();return}const safe=/^(https?:|mailto:)/i.test(url.trim())?url.trim():`https://${url.trim()}`;editor.chain().focus().extendMarkRange('link').setLink({href:safe}).run()};
 return <div className="wysiwyg-shell" style={{'--editor-min-height':`${minHeight}px`} as React.CSSProperties}>
  <div className="wysiwyg-toolbar" role="toolbar" aria-label="Text formatting">
   {cmd('Bold',editor.isActive('bold'),()=>editor.chain().focus().toggleBold().run(),<Bold size={16}/>)}{cmd('Italic',editor.isActive('italic'),()=>editor.chain().focus().toggleItalic().run(),<Italic size={16}/>)}{cmd('Underline',editor.isActive('underline'),()=>editor.chain().focus().toggleUnderline().run(),<UnderlineIcon size={16}/>)}{cmd('Strikethrough',editor.isActive('strike'),()=>editor.chain().focus().toggleStrike().run(),<Strikethrough size={16}/>)}<span className="wysiwyg-separator"/>
   {cmd('Heading 1',editor.isActive('heading',{level:1}),()=>editor.chain().focus().toggleHeading({level:1}).run(),<Heading1 size={17}/>)}{cmd('Heading 2',editor.isActive('heading',{level:2}),()=>editor.chain().focus().toggleHeading({level:2}).run(),<Heading2 size={17}/>)}{cmd('Bulleted list',editor.isActive('bulletList'),()=>editor.chain().focus().toggleBulletList().run(),<List size={17}/>)}{cmd('Numbered list',editor.isActive('orderedList'),()=>editor.chain().focus().toggleOrderedList().run(),<ListOrdered size={17}/>)}<span className="wysiwyg-separator"/>
   {cmd('Quote',editor.isActive('blockquote'),()=>editor.chain().focus().toggleBlockquote().run(),<Quote size={16}/>)}{cmd('Code block',editor.isActive('codeBlock'),()=>editor.chain().focus().toggleCodeBlock().run(),<Code size={16}/>)}{cmd('Insert link',editor.isActive('link'),addLink,<LinkIcon size={16}/>)}{cmd('Horizontal divider',false,()=>editor.chain().focus().setHorizontalRule().run(),<Minus size={16}/>)}<span className="wysiwyg-spacer"/>{cmd('Undo',false,()=>editor.chain().focus().undo().run(),<Undo2 size={16}/>)}{cmd('Redo',false,()=>editor.chain().focus().redo().run(),<Redo2 size={16}/>)}
  </div><EditorContent editor={editor}/>
  <div className="wysiwyg-footer"><span>Rich text</span><span>Formatting is saved with the content</span></div>
 </div>
}
