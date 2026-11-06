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
long used=0; const long cap=long.MaxValue;
var lastCheck=DateTime.MinValue;
void Check(bool force=false){

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



System.Runtime.InteropServices.NativeLibrary.Load("E:/df-extract-20261105/tools/LootDump/bin/Release/net10.0/runtimes/win-x64/native/libSkiaSharp.dll");
TextureDecoder.UseAssetRipperTextureDecoder=true;
var opt=new ExportOptions(exportHdrTexturesAsHdr:false);
var targets=JsonSerializer.Deserialize<string[]>(File.ReadAllText(args[1]))!;
int ok=0;
foreach(var original in targets){
 Check(true);
 var path=original[..original.LastIndexOf('.')]+".uasset";
 try{
 var pkg=p.LoadPackage(path);var texture=pkg.GetExports().OfType<UTexture2D>().Single();
 var vt=texture.PlatformData.VTData;
 if(vt!=null)foreach(var chunk in vt.Chunks){
 var h=chunk.BulkData.Header;var bulkStem=path[..path.LastIndexOf('.')];
 var matching=p.Files.Keys.Where(k=>k.StartsWith(bulkStem,StringComparison.OrdinalIgnoreCase)).ToArray();
 Append("bulk-probe.jsonl",new{original,header=Newtonsoft.Json.JsonConvert.SerializeObject(h),matching,bulkType=chunk.BulkData.GetType().FullName});
 var optional=h.BulkDataFlags.HasFlag(CUE4Parse.UE4.Assets.Objects.EBulkDataFlags.BULKDATA_OptionalPayload);
 var side=bulkStem+(optional?".uptnl":".ubulk");
 var file=p.Files[side];var payload=file.Read();
 Append("sidecar-payload.jsonl",new{original,side,archive=(file as CUE4Parse.UE4.VirtualFileSystem.VfsEntry)?.Vfs.Path,payloadBytes=payload.Length,expected=h.SizeOnDisk,offset=h.OffsetInFile,cooked=h.CookedIndex.ToString()});
 var loaded=chunk.BulkData.Data;Append("bulk-read.jsonl",new{original,bytes=loaded?.Length??0});
}
 int selectedMip=texture.GetFirstMipIndex();
 if(vt!=null){
 bool found=false;
 for(int level=0;level<vt.NumMips;level++){
 bool valid=true;var td=vt.GetTileOffsetData(level);
 for(uint addr=0;addr<td.MaxAddress&&valid;addr++){
 if(!vt.IsValidAddress(level,addr))continue;
 for(uint layer=0;layer<vt.NumLayers;layer++){var(ci,start,len)=vt.GetTileData(level,addr,layer);if(start==~0u)continue;var raw=vt.Chunks[ci].BulkData.Data;if(raw==null||(ulong)start+len>(ulong)raw.Length){valid=false;break;}}
 }
 if(valid){selectedMip=level;found=true;break;}
 }
 if(!found)throw new Exception("no installed mip has complete source tile payload");
 }
 var decoded=texture.DecodeMip(selectedMip,opt)??throw new Exception("actual pixel decode null");
 var bytes=decoded.Encode(opt,out var ext);var stem=Path.GetFileNameWithoutExtension(path);Write(stem+"."+ext,bytes);
 Append("pixels.jsonl",new{sourceObjectPath=original,package=path,archive=(p.Files[path] as CUE4Parse.UE4.VirtualFileSystem.VfsEntry)?.Vfs.Path,output=Path.Combine(output,stem+"."+ext),decoded.Width,decoded.Height,pixelFormat=decoded.PixelFormat.ToString(),virtualTexture=vt!=null,bytes=bytes.Length,sha256=Convert.ToHexString(SHA256.HashData(bytes)),actualPixels=true,mip=selectedMip,highestAvailableCompleteMip=true,advertisedWidth=texture.PlatformData.SizeX,advertisedHeight=texture.PlatformData.SizeY});
 ok++;
 }catch(Exception ex){Append("errors.jsonl",new{sourceObjectPath=original,error=ex.ToString()});}
}
Json("completed.json",new{requested=targets.Length,ok,failed=targets.Length-ok,pid=Environment.ProcessId,time=DateTime.UtcNow});
record Entry(string Path,string Pak,long Size);
