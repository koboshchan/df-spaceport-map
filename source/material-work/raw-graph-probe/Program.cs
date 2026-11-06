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
var output=Path.GetFullPath(@"E:/df-v25-build-20261106/material-work/raw-graph-probe/pass2");
Directory.CreateDirectory(output);
const long cap=60_000_000_000L;
long used=0;
var index=new Dictionary<string,Entry>(StringComparer.OrdinalIgnoreCase);
foreach(var line in File.ReadLines(Path.Combine(root,"index-manifest.jsonl"))){
 using var doc=JsonDocument.Parse(line);var e=doc.RootElement;
 index[e.GetProperty("path").GetString()!]=new(e.GetProperty("path").GetString()!,e.GetProperty("pak").GetString()!,e.GetProperty("size").GetInt64());
}
OodleHelper.Initialize(Path.Combine(root,"tools","oodle-data-shared.dll"));

using var kj=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"community-aes-keys.json")));
var keys=kj.RootElement.GetProperty("Keys").EnumerateArray().GroupBy(x=>x.GetProperty("guid").GetString()).Select(g=>g.First()).ToDictionary(x=>x.GetProperty("guid").GetString()!.Replace("-","").ToUpperInvariant(),x=>x.GetProperty("key").GetString()!);
keys["00000000000000000000000000000000"]=kj.RootElement.GetProperty("MainKey").GetString()!;
using var p=new StreamedFileProvider("DeltaForce",new VersionContainer(EGame.GAME_DeltaForce),StringComparer.OrdinalIgnoreCase);p.Initialize();p.ReadShaderMaps=true;
foreach(var pak in File.ReadAllLines(Path.Combine(root,"pak-paths.txt"))){p.RegisterVfs(pak.Trim());}
foreach(var r in p.UnloadedVfs.ToArray()){var guid=r.EncryptionKeyGuid.ToString().Replace("-","").ToUpperInvariant();if(keys.TryGetValue(guid,out var key))p.SubmitKey(r.EncryptionKeyGuid,new FAesKey(key));}


Directory.CreateDirectory(output);
foreach(var cls in new[]{"MaterialExpressionMaterialFunctionCall","MaterialFunction","Material"}) CUE4Parse.UE4.Assets.ObjectTypeRegistry.RegisterClass(cls,typeof(RawProbe));
var targets=new[]{"DeltaForce/Content/MaterialLib/Materials_HD/Scene/MatBlend/M_MatBlend_Props_Master.uasset","DeltaForce/Content/MaterialLib/MaterialFunctions/Tools/MaterialLayers/DataProvider/MF_TwoLayer_Props_MatBlend.uasset","DeltaForce/Content/MaterialLib/Materials_HD/Scene/Emission/M_SW_NRMAC_Light_CPD_Master_HD.uasset"};
foreach(var path in targets){
 var stem=Path.GetFileNameWithoutExtension(path);
 foreach(var ext in new[]{".uasset",".uexp"}){var f=Path.ChangeExtension(path,ext);if(p.Files.ContainsKey(f)){var bytes=p.SaveAsset(f);File.WriteAllBytes(Path.Combine(output,stem+ext),bytes);File.WriteAllText(Path.Combine(output,stem+ext+".hash"),Convert.ToHexString(SHA256.HashData(bytes)));}}
 var pkg=(Package)p.LoadPackage(path);var exports=new List<object>();
 for(int i=0;i<pkg.ExportMap.Length;i++){var e=pkg.ExportMap[i];try{var obj=pkg.ExportsLazy[i].Value;exports.Add(new{index=i,name=e.ObjectName.Text,cls=e.ClassIndex.Index,template=obj.Template?.GetPathName(),size=e.SerialSize,offset=e.SerialOffset,type=obj.GetType().FullName,source=Newtonsoft.Json.Linq.JObject.Parse(Newtonsoft.Json.JsonConvert.SerializeObject(obj)),probe=obj is RawProbe q?q.evidence:null});}catch(Exception ex){exports.Add(new{index=i,error=ex.ToString()});}}
 File.WriteAllText(Path.Combine(output,stem+".exports.json"),Newtonsoft.Json.JsonConvert.SerializeObject(new{path,exports,imports=pkg.ImportMap.Select(x=>new{name=x.ObjectName.Text,cls=x.ClassName.Text,outer=x.OuterIndex.Index})},Newtonsoft.Json.Formatting.Indented));
}
File.WriteAllText(Path.Combine(output,"completed.json"),"{\"ok\":true}");
public class RawProbe:CUE4Parse.UE4.Assets.Exports.UObject{
 public object? evidence;
 public override void Deserialize(CUE4Parse.UE4.Assets.Readers.FAssetArchive ar,long end){
 var start=ar.Position;var raw=ar.ReadBytes((int)(end-start));ar.Position=start;base.Deserialize(ar,end);var consumed=ar.Position;
 evidence=new{start,end,size=end-start,consumed=consumed-start,tail=end-consumed,rawSHA256=Convert.ToHexString(SHA256.HashData(raw)),tagNames=Properties.Select(x=>x.Name.Text).ToArray(),unversioned=ar.HasUnversionedProperties,rawHex=Convert.ToHexString(raw)};
 }
}
record Entry(string path,string pak,long size);
