export type User={id:number;username:string;full_name:string;email:string;role:string};
export type Project={id:number;key:string;name:string;description:string;owner_name?:string;issue_count:number};
export type Issue={id:number;issue_key:string;project_id:number;project_key:string;project_name:string;parent_id?:number;parent_key?:string;issue_type:string;summary:string;description:string;status:string;priority:string;assignee_id?:number;assignee_name?:string;reporter_name?:string;story_points?:number;due_date?:string;updated_at:string};
export type Doc={id:number;project_id:number;project_key:string;title:string;body:string;author_name?:string;updated_at:string};
