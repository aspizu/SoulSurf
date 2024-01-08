import {ReprocaMethodResponse} from "./reproca.ts";import reproca from "./reproca_config.ts";export async function login(username:string,password:string):Promise<ReprocaMethodResponse<boolean>>{return await reproca.call_method('/login',{username,password})}export async function register(username:string,password:string):Promise<ReprocaMethodResponse<boolean>>{return await reproca.call_method('/register',{username,password})}export async function changepwd(username:string,oldpassword:string,newpassword:string):Promise<ReprocaMethodResponse<boolean>>{return await reproca.call_method('/changepwd',{username,oldpassword,newpassword})}export async function me():Promise<ReprocaMethodResponse<Me>>{return await reproca.call_method('/me',{})}export async function box(url:string):Promise<ReprocaMethodResponse<((Box)|(null))>>{return await reproca.call_method('/box',{url})}export async function create_comment(box:number,content:string):Promise<ReprocaMethodResponse<boolean>>{return await reproca.call_method('/create_comment',{box,content})}export async function create_box(url:string):Promise<ReprocaMethodResponse<boolean>>{return await reproca.call_method('/create_box',{url})}export interface Me{username:string;}export interface Box{id:number;time:number;comments:(Comment)[];}export interface Comment{author:Author;content:string;time:number;}export interface Author{username:string;}