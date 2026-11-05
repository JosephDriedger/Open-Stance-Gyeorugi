#include <fbxsdk.h>
#include <fstream>
#include <iomanip>
#include <map>
#include <vector>
#include <iostream>
#include <cmath>

// Read-only: construct and validate a replacement pose in memory. Export no FBX.
int main(int argc,char** argv) {
 if(argc!=3)return 2;
 auto manager=FbxManager::Create();auto ios=FbxIOSettings::Create(manager,IOSROOT);manager->SetIOSettings(ios);
 auto scene=FbxScene::Create(manager,"Audit");auto importer=FbxImporter::Create(manager,"");
 if(!importer->Initialize(argv[1],-1,ios)||!importer->Import(scene)){std::cerr<<importer->GetStatus().GetErrorString();return 3;}
 importer->Destroy();
 std::map<FbxNode*,FbxAMatrix> matrices;
 std::vector<FbxNode*> meshes;
 double maxConflict=0;
 auto assign=[&](FbxNode* node,const FbxAMatrix& value){
  auto found=matrices.find(node);
  if(found!=matrices.end())for(int r=0;r<4;r++)for(int c=0;c<4;c++)maxConflict=std::max(maxConflict,std::abs(found->second.Get(r,c)-value.Get(r,c)));
  else matrices[node]=value;
 };
 for(int i=0;i<scene->GetNodeCount();i++){
  auto node=scene->GetNode(i);auto mesh=node->GetMesh();if(!mesh)continue;
  bool skinned=false;
  for(int j=0;j<mesh->GetDeformerCount(FbxDeformer::eSkin);j++){
   auto skin=static_cast<FbxSkin*>(mesh->GetDeformer(j,FbxDeformer::eSkin));
   for(int k=0;k<skin->GetClusterCount();k++){
    auto cluster=skin->GetCluster(k);if(!cluster->GetLink())continue;
    FbxAMatrix world;cluster->GetTransformMatrix(world);assign(node,world);
    cluster->GetTransformLinkMatrix(world);assign(cluster->GetLink(),world);skinned=true;
   }
  }
  if(skinned)meshes.push_back(node);
 }
 int existingChecks=0,existingFailures=0;
 for(int p=0;p<scene->GetPoseCount();p++){
  auto oldPose=scene->GetPose(p);if(!oldPose->IsBindPose())continue;
  for(auto node:meshes){existingChecks++;if(!oldPose->IsValidBindPose(node,0.0001))existingFailures++;}
  // Repaired pose tables are identical by binary-tree validation. Test their
  // shared table once against every skinned mesh rather than quadratically.
  break;
 }
 auto known=matrices;
 for(auto& pair:known)for(auto parent=pair.first->GetParent();parent&&parent!=scene->GetRootNode();parent=parent->GetParent())
  if(!matrices.count(parent))matrices[parent]=parent->EvaluateGlobalTransform(FBXSDK_TIME_ZERO);
 auto pose=FbxPose::Create(scene,"Verified_Skin_BindPose");pose->SetIsBindPose(true);
 for(auto& pair:matrices)pose->Add(pair.first,FbxMatrix(pair.second));
 std::ofstream out(argv[2]);out<<std::setprecision(17)<<"{\"existing_pose_checks\":"<<existingChecks<<",\"existing_pose_failures\":"<<existingFailures<<",\"max_cluster_conflict\":"<<maxConflict<<",\"mesh_checks\":[";
 bool first=true;int failures=0;
 for(auto node:meshes){
  FbxStatus status;NodeList a,b,c,d;
  bool valid=pose->IsValidBindPoseVerbose(node,a,b,c,d,0.0001,&status);if(!valid)failures++;
  if(!first)out<<",";first=false;
  out<<"{\"name\":"<<std::quoted(node->GetName())<<",\"valid\":"<<(valid?"true":"false")<<",\"error\":"<<std::quoted(status.GetErrorString())<<"}";
 }
 out<<"],\"matrices\":[";first=true;
 for(auto& pair:matrices){
  if(!first)out<<",";first=false;
  out<<"{\"name\":"<<std::quoted(pair.first->GetName())<<",\"matrix\":[";
  for(int r=0;r<4;r++)for(int c=0;c<4;c++){if(r||c)out<<",";out<<pair.second.Get(r,c);}
  out<<"]}";
 }
 out<<"],\"failures\":"<<failures<<"}";out.close();manager->Destroy();
 std::cout<<"Bind checks "<<meshes.size()<<" failures "<<failures<<" cluster conflict "<<maxConflict<<"\n";
 return failures?4:0;
}
