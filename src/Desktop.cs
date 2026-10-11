// SPDX-License-Identifier: MIT
using System;
using System.IO;
using System.Text;
using System.Linq;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Windows.Automation;
using System.Web.Script.Serialization;
using System.Threading;
using System.Windows.Forms;
using System.Security.Cryptography;
using System.Text.RegularExpressions;
[assembly: System.Reflection.AssemblyTitle("XQ Compile Runner")]
[assembly: System.Reflection.AssemblyProduct("XQ Compile Runner")]
[assembly: System.Reflection.AssemblyVersion("0.1.0.0")]
[assembly: System.Reflection.AssemblyFileVersion("0.1.0.0")]
public class Desktop {
 public delegate bool EnumProc(IntPtr h,IntPtr l);
 [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc f,IntPtr p);
 [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr h,EnumProc f,IntPtr p);
 [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32.dll")] public static extern bool IsWindowEnabled(IntPtr h);
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h,out uint p);
 [DllImport("user32.dll")] public static extern int GetDlgCtrlID(IntPtr h);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h,StringBuilder b,int n);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h,StringBuilder b,int n);
 [DllImport("user32.dll",EntryPoint="SendMessageTimeoutA",SetLastError=true)] public static extern IntPtr TextA(IntPtr h,uint m,IntPtr w,byte[] b,uint flags,uint ms,out IntPtr result);
 [DllImport("user32.dll",SetLastError=true)] public static extern IntPtr SendMessageTimeout(IntPtr h,uint m,IntPtr w,IntPtr l,uint flags,uint ms,out IntPtr result);
 [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h,uint m,IntPtr w,IntPtr l);
 [DllImport("user32.dll")] public static extern IntPtr GetWindow(IntPtr h,uint cmd);
 [DllImport("user32.dll")] public static extern bool IsChild(IntPtr p,IntPtr c);
 [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
 [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
 [DllImport("user32.dll")] public static extern uint GetClipboardSequenceNumber();
 [DllImport("user32.dll")] static extern IntPtr OpenInputDesktop(uint flags,bool inherit,uint access);
 [DllImport("user32.dll")] static extern bool CloseDesktop(IntPtr h);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern bool GetUserObjectInformation(IntPtr h,int index,StringBuilder text,int length,out int needed);
 public static string Title(IntPtr h){var b=new StringBuilder(2048);GetWindowText(h,b,b.Capacity);return b.ToString();}
 public static string Class(IntPtr h){var b=new StringBuilder(256);GetClassName(h,b,b.Capacity);return b.ToString();}
 public static List<IntPtr> Children(IntPtr h){var r=new List<IntPtr>();EnumChildWindows(h,(w,l)=>{r.Add(w);return true;},IntPtr.Zero);return r;}
 public static List<IntPtr> Windows(){var r=new List<IntPtr>();EnumWindows((w,l)=>{r.Add(w);return true;},IntPtr.Zero);return r;}
 public static int Pid(IntPtr h){uint p;GetWindowThreadProcessId(h,out p);return (int)p;}
 public static string AnsiText(IntPtr h){byte[] b=new byte[131072];IntPtr r;if(TextA(h,13,new IntPtr(b.Length),b,2,1000,out r)==IntPtr.Zero)throw new Exception("TEXT_TIMEOUT");int n=Array.IndexOf(b,(byte)0);if(n<0)n=b.Length;return Encoding.GetEncoding(950).GetString(b,0,n);}
 public static JavaScriptSerializer Json=new JavaScriptSerializer(){MaxJsonLength=4000000};
 static DateTime Deadline=DateTime.MaxValue;
 static uint OwnedClip=0;
 static string Stage="initial";
 static bool OwnMenu=false;
 static IntPtr OriginalEditor=IntPtr.Zero;
 static void CheckTime(){if(DateTime.UtcNow>Deadline)throw new Exception("DESKTOP_TIMEOUT: "+Stage);}
 static string Hash(string s){using(var h=SHA256.Create()){return BitConverter.ToString(h.ComputeHash(Encoding.UTF8.GetBytes(s.Replace("\r\n","\n").Trim()))).Replace("-","").ToLowerInvariant();}}
 [STAThread] public static int Main(string[] args){
  try {
   Console.OutputEncoding=new UTF8Encoding(false);
   if(args.Length>0&&args[0]=="health"){Console.WriteLine("{\"version\":\"0.1.0\",\"target\":\""+Target+"\",\"execution\":\"compile-only\"}");return 0;}
   if(args.Length==4&&args[0]=="run"){LoadConfig(args[1]);return Run(args[2],args[3]);}
   throw new Exception("USAGE: health | run CONFIG INPUT OUTPUT");
  }catch(Exception e){Console.WriteLine(Json.Serialize(new {error=e.Message}));return 1;}
 }
 public const string Target="OSS_CompileProbe";
 static string ExpectedProcessPath;
 static void LoadConfig(string path){
  var config=Json.Deserialize<Dictionary<string,object>>(File.ReadAllText(path,Encoding.UTF8));
  ExpectedProcessPath=(string)config["xq_executable"];
  if(String.IsNullOrWhiteSpace(ExpectedProcessPath)||!Path.IsPathRooted(ExpectedProcessPath)||
     !File.Exists(ExpectedProcessPath)||!String.Equals(Path.GetFileName(ExpectedProcessPath),"daqxqlite.exe",StringComparison.OrdinalIgnoreCase))
   throw new Exception("INVALID_XQ_PATH");
  ExpectedProcessPath=Path.GetFullPath(ExpectedProcessPath);
 }
 static IntPtr Bind(){
  var all=Windows().Where(h=>IsWindowVisible(h)&&Title(h).StartsWith("XScript 編輯器")).ToList();
  if(all.Count!=1)throw new Exception("WINDOW_MISMATCH: expected exactly one XScript editor");
  IntPtr editor=all[0];
  if(!String.Equals(Process.GetProcessById(Pid(editor)).MainModule.FileName,ExpectedProcessPath,StringComparison.OrdinalIgnoreCase))throw new Exception("PROCESS_MISMATCH");
  Guard(editor);return editor;
 }
 static void Guard(IntPtr editor){
  CheckTime();
  if(OriginalEditor!=IntPtr.Zero&&editor!=OriginalEditor)throw new Exception("WINDOW_CHANGED");
  var desktop=OpenInputDesktop(0,false,1);
  if(desktop==IntPtr.Zero)throw new Exception("DESKTOP_UNAVAILABLE_OR_LOCKED");
  try{var name=new StringBuilder(256);int needed;if(!GetUserObjectInformation(desktop,2,name,512,out needed)||name.ToString()!="Default")throw new Exception("DESKTOP_UNAVAILABLE_OR_LOCKED");}finally{CloseDesktop(desktop);}
  if(!IsWindowVisible(editor))throw new Exception("WINDOW_MISSING");
  if(!IsWindowEnabled(editor))throw new Exception("POPUP_BLOCKED: editor disabled");
  string title=Title(editor);string prefix="XScript 編輯器 - ["+Target+"(交易)";
  if(!title.StartsWith(prefix)||!(title==prefix+"]"||title==prefix+"未編譯]"||title==prefix+"*]"||title==prefix+"未編譯*]"))throw new Exception("WINDOW_MISMATCH: "+title);
  var dialogs=Windows().Where(h=>IsWindowVisible(h)&&Pid(h)==Pid(editor)&&Class(h)=="#32770").ToList();
  if(dialogs.Count>0)throw new Exception("POPUP_BLOCKED: "+Title(dialogs[0]));
  var unexpected=Windows().Where(h=>IsWindowVisible(h)&&Pid(h)==Pid(editor)&&h!=editor&&Class(h)!="DAQXQLITEMainWnd"&&Class(h)!="tooltips_class32"&&!(OwnMenu&&Class(h)=="#32768")).ToList();
  if(unexpected.Count>0)throw new Exception("POPUP_BLOCKED: unexpected "+Class(unexpected[0])+" "+Title(unexpected[0]));
 }
 static IntPtr Source(IntPtr editor){
  var matches=Children(editor).Where(c=>Class(c)=="Scintilla"&&GetDlgCtrlID(c)==9999&&IsWindowVisible(c)).ToList();
  if(matches.Count!=1)throw new Exception("SOURCE_MISMATCH");return matches[0];
 }
 static IntPtr Send(IntPtr h,uint m,IntPtr w,IntPtr l){IntPtr r;if(SendMessageTimeout(h,m,w,l,2,1500,out r)==IntPtr.Zero)throw new Exception("CONTROL_TIMEOUT");return r;}
 static string CopyScintilla(IntPtr editor,IntPtr source){
  Guard(editor);if(!IsChild(editor,source)||Class(source)!="Scintilla")throw new Exception("CONTROL_MISMATCH");
  if(Send(source,2006,IntPtr.Zero,IntPtr.Zero)==IntPtr.Zero)return "";
  uint before=GetClipboardSequenceNumber();Send(source,2013,IntPtr.Zero,IntPtr.Zero);Guard(editor);Send(source,2178,IntPtr.Zero,IntPtr.Zero);
  for(int i=0;i<20;i++){if(GetClipboardSequenceNumber()!=before&&Clipboard.ContainsText()){OwnedClip=GetClipboardSequenceNumber();return Clipboard.GetText();}CheckTime();Thread.Sleep(50);}
  throw new Exception("CLIPBOARD_TIMEOUT");
 }
 static AutomationElement NamedButton(IntPtr editor,string name){
  Guard(editor);var root=AutomationElement.FromHandle(editor);
  var found=root.FindAll(TreeScope.Descendants,new PropertyCondition(AutomationElement.ControlTypeProperty,ControlType.Button)).Cast<AutomationElement>().Where(e=>e.Current.Name.Trim()==name&&!e.Current.IsOffscreen&&e.Current.IsEnabled).ToList();
  if(found.Count!=1)throw new Exception("BUTTON_MISMATCH: "+name+" count="+found.Count);
  return found[0];
 }
 static void InvokeButton(IntPtr editor,string name){
  var e=NamedButton(editor,name);object p;if(!e.TryGetCurrentPattern(InvokePattern.Pattern,out p))throw new Exception("BUTTON_NOT_INVOKABLE: "+name);
  Guard(editor);((InvokePattern)p).Invoke();Thread.Sleep(100);Guard(editor);
 }
 static string WaitSummary(IntPtr editor,IntPtr log,string previous,bool forceTimeout){
  for(;;){
   Guard(editor);
   string s=CopyScintilla(editor,log);
   if(!forceTimeout&&s!=previous&&Regex.IsMatch(s,Regex.Escape(Target)+@" 編譯(成功|發生錯誤)，\s*\d+項錯誤，\s*\d+項警告"))return s;
   Thread.Sleep(200);
  }
 }
 static int Run(string input,string output){
  var trace=new List<string>();System.Windows.Forms.IDataObject originalClipboard=null;
  var result=new Dictionary<string,object>();result["ok"]=false;
  try{
   var req=Json.Deserialize<Dictionary<string,object>>(File.ReadAllText(input,Encoding.UTF8));
   if(req.Count!=4||!req.ContainsKey("code")||!req.ContainsKey("target")||!req.ContainsKey("sha256")||!req.ContainsKey("timeout_seconds"))throw new Exception("UNSUPPORTED_FIELDS");
   string code=(string)req["code"];
   if(String.IsNullOrWhiteSpace(code)||!(req["timeout_seconds"] is int))throw new Exception("INVALID_REQUEST");
   int seconds=Convert.ToInt32(req["timeout_seconds"]);if(seconds<1||seconds>45)throw new Exception("INVALID_TIMEOUT");
   Deadline=DateTime.UtcNow.AddSeconds(seconds);
   if((string)req["target"]!=Target||code.Length==0||code.Length>20000||code.IndexOf('\0')>=0||Hash(code)!=(string)req["sha256"])throw new Exception("REQUEST_MISMATCH");
   Stage="preflight";
   IntPtr editor=Bind();OriginalEditor=editor;IntPtr source=Source(editor);
   if(Send(source,2159,IntPtr.Zero,IntPtr.Zero)!=IntPtr.Zero)throw new Exception("UNSAVED_TEST_DOCUMENT: save your edits first");
   originalClipboard=Clipboard.GetDataObject();
   trace.Add("preflight_guard_pass");string before=CopyScintilla(editor,source);
   File.WriteAllText(Path.Combine(Path.GetDirectoryName(output),"source-before.xs"),before,Encoding.UTF8);
   var logs=Children(editor).Where(c=>Class(c)=="Scintilla"&&GetDlgCtrlID(c)==59751).ToList();
   if(logs.Count!=1)throw new Exception("LOG_CONTROL_MISMATCH");IntPtr log=logs[0];
   string previous=CopyScintilla(editor,log);
   Stage="write";Guard(editor);Clipboard.SetText(code);OwnedClip=GetClipboardSequenceNumber();
   Send(source,2013,IntPtr.Zero,IntPtr.Zero);Guard(editor);
   if(Clipboard.GetText()!=code||OwnedClip!=GetClipboardSequenceNumber())throw new Exception("CLIPBOARD_CHANGED");
   Send(source,2179,IntPtr.Zero,IntPtr.Zero);trace.Add("source_pasted");Guard(editor);
   string readback=CopyScintilla(editor,source);
   if(Hash(readback)!=(string)req["sha256"])throw new Exception("SOURCE_HASH_MISMATCH");
   trace.Add("source_hash_verified");
   Stage="save";InvokeButton(editor,"儲存");
   if(Send(source,2159,IntPtr.Zero,IntPtr.Zero)!=IntPtr.Zero||Title(editor).Contains("*"))throw new Exception("SAVE_NOT_CONFIRMED");
   trace.Add("saved");
   // Make no UI decisions from a cached control tree. Resolve the button again.
   Stage="compile";double epoch=(DateTime.UtcNow-new DateTime(1970,1,1)).TotalSeconds;
   InvokeButton(editor,"編譯");trace.Add("compile_invoked");
   bool force=false;
   string summary=WaitSummary(editor,log,previous,force);trace.Add("fresh_summary_captured");
   var m=Regex.Match(summary,Regex.Escape(Target)+@" 編譯(成功|發生錯誤)，\s*(\d+)項錯誤，\s*(\d+)項警告");
   string errors="";
   if(int.Parse(m.Groups[2].Value)>0){Stage="errors";errors=CopyErrorGrid(editor);trace.Add("errors_captured");}
   Stage="final_verify";Guard(editor);if(Hash(CopyScintilla(editor,source))!=(string)req["sha256"])throw new Exception("SOURCE_CHANGED_DURING_COMPILE");
   result["compile_passed"]=int.Parse(m.Groups[2].Value)==0;result["error_count"]=int.Parse(m.Groups[2].Value);result["warning_count"]=int.Parse(m.Groups[3].Value);
   result["ok"]=true;result["summary"]=summary;result["errors"]=errors;result["source_readback"]=readback;result["compile_epoch"]=epoch;
  }catch(Exception e){result["error"]=e.Message;result["stage"]=Stage;}
  finally{
   // Restore only our clipboard contents; never overwrite a newer user copy.
   try{if(originalClipboard!=null&&OwnedClip==GetClipboardSequenceNumber())Clipboard.SetDataObject(originalClipboard,true);}catch{}
   result["trace"]=trace;File.WriteAllText(output,Json.Serialize(result),new UTF8Encoding(false));
  }
  Console.WriteLine(Json.Serialize(result));return (bool)result["ok"]?0:1;
 }
 static string CopyErrorGrid(IntPtr editor){
  Guard(editor);var grids=Children(editor).Where(c=>Class(c)=="XTPReport"&&GetDlgCtrlID(c)==59752).ToList();
  if(grids.Count!=1)throw new Exception("ERROR_GRID_MISMATCH");
  IntPtr grid=grids[0];
  if(!IsWindowVisible(grid))throw new Exception("ERROR_GRID_NOT_VISIBLE");
  // The native report context menu supports select-all and copy, unlike Ctrl+C.
  MenuCommand(editor,grid,"全部選取");
  uint old=GetClipboardSequenceNumber();MenuCommand(editor,grid,"複製");
  if(GetClipboardSequenceNumber()==old||!Clipboard.ContainsText())throw new Exception("ERROR_CLIPBOARD_NOT_FRESH");
  OwnedClip=GetClipboardSequenceNumber();return Clipboard.GetText();
 }
 static void MenuCommand(IntPtr editor,IntPtr grid,string name){
  Guard(editor);OwnMenu=true;PostMessage(grid,0x007B,grid,new IntPtr(-1));
  for(int i=0;i<20;i++){
   CheckTime();Thread.Sleep(100);
   var roots=Windows().Where(h=>IsWindowVisible(h)&&Pid(h)==Pid(editor)&&Class(h)=="#32768").ToList();
   var candidates=new List<AutomationElement>();
   foreach(var h in roots){
    var e=AutomationElement.FromHandle(h);
    candidates.AddRange(e.FindAll(TreeScope.Descendants,Condition.TrueCondition).Cast<AutomationElement>().Where(x=>x.Current.Name.Trim()==name&&x.Current.IsEnabled&&!x.Current.IsOffscreen));
   }
   if(candidates.Count==1){object pattern;if(!candidates[0].TryGetCurrentPattern(InvokePattern.Pattern,out pattern))throw new Exception("MENU_NOT_INVOKABLE");((InvokePattern)pattern).Invoke();Thread.Sleep(100);OwnMenu=false;Guard(editor);return;}
  }
  throw new Exception("MENU_NOT_FOUND: "+name);
 }
}
