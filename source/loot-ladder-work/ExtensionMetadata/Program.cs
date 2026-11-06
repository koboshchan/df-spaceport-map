using System.Text.Json;
using System.Diagnostics;
using System.Reflection;
using System.Security.Cryptography;
using CUE4Parse.FileProvider;
using CUE4Parse.UE4.Versions;
using CUE4Parse.Encryption.Aes;
using CUE4Parse.Compression;
using CUE4Parse.UE4.Assets;
using CUE4Parse.UE4.Assets.Exports.Texture;

using CUE4Parse.UE4.Assets.Exports.Material;
using CUE4Parse_Conversion;
using CUE4Parse_Conversion.Options;
using CUE4Parse_Conversion.Textures;
using CUE4Parse_Conversion.Exporters;
using Serilog;
Log.Logger=new LoggerConfiguration().MinimumLevel.Error().WriteTo.Console().CreateLogger();
var root=@"E:\df-extract-20261105";
var output=args[0];
Directory.CreateDirectory(output);
const long cap=60_000_000_000L;
long used=Directory.EnumerateFiles(root,"*",SearchOption.AllDirectories).Sum(f=>new FileInfo(f).Length);
var lastCheck=DateTime.MinValue;
void Check(bool force=false){
 if(used>cap-256_000_000)throw new OperationCanceledException("60GB cumulative cap reached");
 if(new DriveInfo("E").AvailableFreeSpace<20_000_000_000L)throw new OperationCanceledException("20GB disk reserve reached");
 if(!force && (DateTime.UtcNow-lastCheck).TotalSeconds<10)return;
 var psi=new ProcessStartInfo("powershell.exe"){UseShellExecute=false,RedirectStandardOutput=true,RedirectStandardError=true,CreateNoWindow=true};
 psi.ArgumentList.Add("-NoProfile");psi.ArgumentList.Add("-File");psi.ArgumentList.Add(Path.Combine(output,"guard.ps1"));
 using var proc=Process.Start(psi)!;var result=proc.StandardOutput.ReadToEnd();proc.WaitForExit();
 if(proc.ExitCode!=0)throw new OperationCanceledException("DF/ACE guard stop "+result);
 lastCheck=DateTime.UtcNow;
}
void Write(string relative,byte[] bytes){
 Check(); var path=Path.GetFullPath(Path.Combine(output,relative));
 if(!path.StartsWith(output+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))throw new Exception("unsafe output path");
 if(used+bytes.LongLength+256_000_000>cap)throw new OperationCanceledException("60GB cumulative cap");
 Directory.CreateDirectory(Path.GetDirectoryName(path)!); File.WriteAllBytes(path,bytes); used+=bytes.LongLength;
}
void Json(string relative,object value)=>Write(relative,System.Text.Encoding.UTF8.GetBytes(JsonSerializer.Serialize(value,new JsonSerializerOptions{IncludeFields=true})));
void Append(string relative,object value){
 Check();var text=JsonSerializer.Serialize(value,new JsonSerializerOptions{IncludeFields=true})+Environment.NewLine;
 var bytes=System.Text.Encoding.UTF8.GetByteCount(text);if(used+bytes+16_000_000>cap)throw new OperationCanceledException("60GB cap");
 File.AppendAllText(Path.Combine(output,relative),text);used+=bytes;
}
Check(true);
File.WriteAllText(Path.Combine(output,"worker.pid"),Environment.ProcessId.ToString());
var index=new Dictionary<string,Entry>(StringComparer.OrdinalIgnoreCase);
foreach(var line in File.ReadLines(Path.Combine(root,"index-manifest.jsonl"))){
 using var doc=JsonDocument.Parse(line);var e=doc.RootElement;
 index[e.GetProperty("path").GetString()!]=new(e.GetProperty("path").GetString()!,e.GetProperty("pak").GetString()!,e.GetProperty("size").GetInt64());
}
OodleHelper.Initialize(Path.Combine(root,"tools","oodle-data-shared.dll"));

using var kj=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"community-aes-keys.json")));
var keys=kj.RootElement.GetProperty("Keys").EnumerateArray().GroupBy(x=>x.GetProperty("guid").GetString()).Select(g=>g.First()).ToDictionary(x=>x.GetProperty("guid").GetString()!.Replace("-","").ToUpperInvariant(),x=>x.GetProperty("key").GetString()!);
keys["00000000000000000000000000000000"]=kj.RootElement.GetProperty("MainKey").GetString()!;
using var p=new StreamedFileProvider("DeltaForce",new VersionContainer(EGame.GAME_DeltaForce),StringComparer.OrdinalIgnoreCase);p.Initialize();
foreach(var pak in File.ReadAllLines(Path.Combine(root,"pak-paths.txt"))){Check();p.RegisterVfs(pak.Trim());}
foreach(var r in p.UnloadedVfs.ToArray()){Check();var guid=r.EncryptionKeyGuid.ToString().Replace("-","").ToUpperInvariant();if(keys.TryGetValue(guid,out var key))p.SubmitKey(r.EncryptionKeyGuid,new FAesKey(key));}

CUE4Parse.UE4.Assets.ObjectTypeRegistry.RegisterClass("VirtualMaterialInstanceConstant",typeof(CUE4Parse.GameTypes.DFHO.Assets.Exports.UVirtualMaterialInstanceConstant));




var resolution=Path.Combine(root,"placements","validation","resolution");
var queue=new Queue<string>();var queued=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
string? PackagePath(string reference){
 var r=reference;
 var quote=r.IndexOf('\'');if(quote>=0)r=r[(quote+1)..].TrimEnd('\'');
 var dot=r.IndexOf('.');if(dot>=0)r=r[..dot];
 var colon=r.IndexOf(':');if(colon>=0)r=r[..colon];
 if(r.StartsWith("/Game/"))r="DeltaForce/Content/"+r[6..];
 else if(r.StartsWith("/Engine/"))r="Engine/Content/"+r[8..];
 if(r.StartsWith("/Script/"))return null;
 foreach(var e in new[]{".uasset",".umap"})if(p.Files.ContainsKey(r+e))return r+e;
 if(p.Files.ContainsKey(r))return r;
 return null;
}
void Enqueue(string? reference,string reason){
 if(reference==null)return;
 var path=PackagePath(reference);
 if(path==null){Append("reference-misses.jsonl",new{reference,reason});return;}
 if(queued.Add(path)){if(queued.Count>5000)throw new Exception("targeted metadata package bound exceeded");queue.Enqueue(path);Append("queue.jsonl",new{path,reference,reason});}
}
foreach(var name in new[]{"AsyncStaticMeshComponent","DFMDesStaticMeshComponent","SplineMeshComponent","InteractorAsyncStaticMeshComponent"})CUE4Parse.UE4.Assets.ObjectTypeRegistry.RegisterClass(name,typeof(SceneProbe));
CUE4Parse.UE4.Assets.ObjectTypeRegistry.RegisterClass("CustomWorldComposition",typeof(CompositionProbe));
foreach(var parent in new[]{"DeltaForce/Content/BluePrints/Interact/Animation/ABP_MilitaryBox7.uasset","DeltaForce/Content/BluePrints/Interact/BP_Interact_AnimSwitcherContainer.uasset"})Enqueue(parent,"parent graph");
foreach(var x in p.Files.Keys.Where(x=>x.EndsWith(".uasset") && (new[]{"props_container_Locker_797/","props_collect_box_589/","props_collect_box_1092/"}.Any(s=>x.Contains(s,StringComparison.OrdinalIgnoreCase)) || new[]{"ABP_ClothGrab.uasset","ABP_VendingMac.uasset","ABP_SingleItemContainer_Cabinet.uasset","ABP_Militarybox3_New1.uasset","BP_ContainerAnimSwitcherComponent.uasset","BP_InteractorContainer_Cloth_Grab.uasset","BP_Interactor_SingleItemContainer_Cabinet.uasset","BP_Interactor_SingleItemContainer_Cabinet_1.uasset","BP_Interactor_SingleItemContainer_WeaponBox.uasset","BP_Interactor_SingleItemContainer_WeaponBoxnew.uasset"}.Any(s=>x.EndsWith(s,StringComparison.OrdinalIgnoreCase))))) Enqueue(x,"all canonical model assets and animation graph");
Json("candidate-index.json",p.Files.Keys.Where(x=>x.EndsWith(".uasset") && new[]{"589","797","1092"}.Any(s=>x.Contains("props_collect_box_"+s,StringComparison.OrdinalIgnoreCase))).ToArray());
var skipped=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
int parsed=0,failed=0,extracted=0;var watch=Stopwatch.StartNew();
while(queue.TryDequeue(out var path)){
 Check();
 try{
  var pkg=p.LoadPackage(path) as Package??throw new Exception("not regular package");
  var serials=new List<object>();
  for(int i=0;i<pkg.ExportsLazy.Length;i++){
   Check();
   try{
    var obj=pkg.ExportsLazy[i].Value;
    if(obj is CUE4Parse.UE4.Assets.Exports.StaticMesh.UStaticMesh || obj is UTexture) {skipped.Add(obj.GetPathName());continue;}
    var raw=Newtonsoft.Json.Linq.JObject.Parse(Newtonsoft.Json.JsonConvert.SerializeObject(obj));
    var extra=obj is ProbeBase probe?new{probe.tailBytes,probe.tailHex,probe.tailStart,probe.tailEnd}:null;
    string rel="objects/"+path[..path.LastIndexOf('.')]+"/"+i.ToString("D6")+".json";
    Json(rel,new{package=path,objectPath=obj.GetPathName(),className=obj.ExportType,parserType=obj.GetType().FullName,template=obj.Template?.GetPathName(),outer=obj.Outer?.GetPathName(),classPath=obj.Class?.GetPathName(),super=obj.Super?.GetPathName(),source=JsonDocument.Parse(raw.ToString()).RootElement.Clone(),probe=extra});
    Append("objects.jsonl",new{package=path,objectPath=obj.GetPathName(),className=obj.ExportType,metadata=rel,template=obj.Template?.GetPathName(),outer=obj.Outer?.GetPathName(),super=obj.Super?.GetPathName()});extracted++;
    
    
    foreach(var val in raw.Descendants().OfType<Newtonsoft.Json.Linq.JProperty>().Where(v=>v.Name=="ObjectPath").Select(v=>v.Value.ToString())) if(!val.StartsWith("/Script/") && (val.Contains("/Animation/") || val.Contains("/Anims/") || val.Contains("/Anim/") || val.Contains("ABP_"))) Enqueue(val,"target animation dependency");
    serials.Add(new{index=i,path=obj.GetPathName(),cls=obj.ExportType,serialSize=pkg.ExportMap[i].SerialSize,serialOffset=pkg.ExportMap[i].SerialOffset,probe=extra});
   }catch(OperationCanceledException){throw;}catch(Exception ex){Append("object-failures.jsonl",new{path,index=i,error=ex.ToString()});}
  }
  Json("packages/"+path[..path.LastIndexOf('.')]+".json",new{package=path,imports=pkg.ImportMap.Select(x=>new{name=x.ObjectName.Text,cls=x.ClassName.Text,outer=x.OuterIndex.Index}).ToArray(),exports=serials});
  parsed++;
 }catch(OperationCanceledException){throw;}catch(Exception ex){failed++;Append("failures.jsonl",new{path,error=ex.ToString()});}
 Json("status.json",new{pid=Environment.ProcessId,parsed,failed,extracted,queued=queue.Count,candidates=queued.Count,elapsedSeconds=watch.Elapsed.TotalSeconds,time=DateTime.UtcNow});
 if(parsed%20==0)GC.Collect();
}
Json("completed.json",new{parsed,failed,extracted,queued=queue.Count,candidates=queued.Count,skippedMeshesOrTextures=skipped.Count,elapsedSeconds=watch.Elapsed.TotalSeconds,time=DateTime.UtcNow});
public class ProbeBase:CUE4Parse.UE4.Assets.Exports.UObject{
 public long tailBytes,tailStart,tailEnd;public string? tailHex;
 public override void Deserialize(CUE4Parse.UE4.Assets.Readers.FAssetArchive ar,long validPos){
  base.Deserialize(ar,validPos);tailStart=ar.Position;tailEnd=validPos;tailBytes=validPos-ar.Position;
  if(tailBytes>0)tailHex=Convert.ToHexString(ar.ReadBytes((int)Math.Min(tailBytes,262144)));
 }
}
public class CompositionProbe:ProbeBase{}
public class SceneProbe:CUE4Parse.UE4.Assets.Exports.Component.USceneComponent{}

record Entry(string path,string pak,long size);
