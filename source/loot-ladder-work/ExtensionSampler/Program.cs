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
var output=args.Length>0?args[0]:Path.Combine(root,"loot-skeletal");
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
void Json(string relative,object value)=>Write(relative,System.Text.Encoding.UTF8.GetBytes(JsonSerializer.Serialize(value)));
void Append(string relative,object value){
 Check();var text=JsonSerializer.Serialize(value)+Environment.NewLine;
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



var pairs=JsonSerializer.Deserialize<string[][]>(File.ReadAllText(args[1]))!;
var jo=new JsonSerializerOptions{IncludeFields=true};
foreach(var pair in pairs){
 Check(true);
 try{
 var mesh=p.LoadPackage(pair[0]).ExportsLazy.Select(x=>x.Value).OfType<CUE4Parse.UE4.Assets.Exports.Engine.USkinnedAsset>().First();
 var anim=p.LoadPackage(pair[1]).ExportsLazy.Select(x=>x.Value).OfType<CUE4Parse.UE4.Assets.Exports.Animation.UAnimSequence>().First();
 var set=CUE4Parse_Conversion.Animations.AnimConverter.ConvertAnims(anim);
 var seq=set.Sequences.Single();
 var mr=mesh.ReferenceSkeleton;var sr=set.Skeleton.ReferenceSkeleton;
 var bones=new List<object>(); double maxP=0,maxQ=0,maxS=0;int missing=0,keyCount=0;
 for(int i=0;i<mr.FinalRefBoneInfo.Length;i++){
 var bi=mr.FinalRefBoneInfo[i];var rest=mr.FinalRefBonePose[i];
 var si=Array.FindIndex(sr.FinalRefBoneInfo,b=>b.Name.Text==bi.Name.Text);
 if(si<0){missing++;continue;}
 var frames=new List<object>();
 foreach(var frame in new[]{0,Math.Max(0,seq.NumFrames/2),Math.Max(0,seq.NumFrames-1)}.Distinct()){
 var q=rest.Rotation;var t=rest.Translation;var s=rest.Scale3D;
 if(si<seq.Tracks.Count){var tr=seq.Tracks[si];if(tr.HasKeys())keyCount++;tr.GetBoneTransform(frame,seq.NumFrames,ref q,ref t,ref s);seq.RetargetBoneTransform(si,rest,ref q,ref t,ref s);}
 double dp=(t-rest.Translation).Size();double ds=(s-rest.Scale3D).Size();
 double dot=q.X*rest.Rotation.X+q.Y*rest.Rotation.Y+q.Z*rest.Rotation.Z+q.W*rest.Rotation.W;
 double norm=Math.Sqrt((q.X*q.X+q.Y*q.Y+q.Z*q.Z+q.W*q.W)*(rest.Rotation.X*rest.Rotation.X+rest.Rotation.Y*rest.Rotation.Y+rest.Rotation.Z*rest.Rotation.Z+rest.Rotation.W*rest.Rotation.W));
 double dq=2*Math.Acos(Math.Clamp(Math.Abs(dot)/norm,0,1));
 maxP=Math.Max(maxP,dp);maxQ=Math.Max(maxQ,dq);maxS=Math.Max(maxS,ds);
 frames.Add(new{frame,translation=new[]{t.X,t.Y,t.Z},rotation=new[]{q.X,q.Y,q.Z,q.W},scale=new[]{s.X,s.Y,s.Z},dp,dq,ds});
 }
 bones.Add(new{name=bi.Name.Text,parent=bi.ParentIndex,rest=new{translation=new[]{rest.Translation.X,rest.Translation.Y,rest.Translation.Z},rotation=new[]{rest.Rotation.X,rest.Rotation.Y,rest.Rotation.Z,rest.Rotation.W},scale=new[]{rest.Scale3D.X,rest.Scale3D.Y,rest.Scale3D.Z}},frames});
 }
 Append("samples.jsonl",new{mesh=pair[0],animation=pair[1],pid=Environment.ProcessId,frames=seq.NumFrames,duration=seq.AnimEndTime,fps=seq.FramesPerSecond,additive=seq.IsAdditive,tracks=seq.Tracks.Count,keyCount,missing,maxTranslationCm=maxP,maxRotationRadians=maxQ,maxScale=maxS,refEqual=maxP<0.001&&maxQ<0.0001&&maxS<0.00001&&missing==0,bones});
 }catch(Exception ex){Append("errors.jsonl",new{pair,error=ex.ToString()});}
}
Json("completed.json",new{pid=Environment.ProcessId,pairs=pairs.Length,time=DateTime.UtcNow});
record Entry(string path,string pak,long size);
