# -*- coding: utf-8 -*-
"""
Created on Fri Jun 26 11:02:19 2020

@author: richieBao-caDesign设计(cadesign.cn)
"""

#位于百度地图POI数据的抓取与地理空间点地图/1. 百度地图POI数据的抓取-单个分类实现与地理空间点地图/1.1 单个分类POI爬取
def baiduPOI_dataCrawler(query_dic,bound_coordinate,partition,page_num_range,poi_fn_list=False):
    #所调用的库及辅助文件
    import coordinate_transformation as cc    
    import urllib, json, csv,os,pathlib
    
    '''function-百度地图开放平台POI数据爬取'''
    urlRoot='http://api.map.baidu.com/place/v2/search?' #数据下载网址，查询百度地图服务文档
    #切分检索区域
    xDis=(bound_coordinate['rightTop'][0]-bound_coordinate['leftBottom'][0])/partition
    yDis=(bound_coordinate['rightTop'][1]-bound_coordinate['leftBottom'][1])/partition    
    #判断是否要写入文件
    if poi_fn_list:
        for file_path in poi_fn_list:
            fP=pathlib.Path(file_path)
            if fP.suffix=='.csv':
                poi_csv=open(fP,'w',encoding='utf-8')
                csv_writer=csv.writer(poi_csv)    
            elif fP.suffix=='.json':
                poi_json=open(fP,'w',encoding='utf-8')
    num=0
    jsonDS=[] #存储读取的数据，用于.json格式数据的保存
    #循环切分的检索区域，逐区下载数据
    print("Start downloading data...")
    for i in range(partition):
        for j in range(partition):
            leftBottomCoordi=[bound_coordinate['leftBottom'][0]+i*xDis,bound_coordinate['leftBottom'][1]+j*yDis]
            rightTopCoordi=[bound_coordinate['leftBottom'][0]+(i+1)*xDis,bound_coordinate['leftBottom'][1]+(j+1)*yDis]
            for p in page_num_range:  
                #更新请求参数
                query_dic.update({'page_num':str(p),
                                  'bounds':str(leftBottomCoordi[1]) + ',' + str(leftBottomCoordi[0]) + ','+str(rightTopCoordi[1]) + ',' + str(rightTopCoordi[0]),
                                  'output':'json',
                                 })

                url=urlRoot+urllib.parse.urlencode(query_dic)
                data=urllib.request.urlopen(url)
                responseOfLoad=json.loads(data.read()) 
                if responseOfLoad.get("message")=='ok':
                    results=responseOfLoad.get("results") 
                    for row in range(len(results)):
                        subData=results[row]
                        baidu_coordinateSystem=[subData.get('location').get('lng'),subData.get('location').get('lat')] #获取百度坐标系
                        Mars_coordinateSystem=cc.bd09togcj02(baidu_coordinateSystem[0], baidu_coordinateSystem[1]) #百度坐标系-->火星坐标系
                        WGS84_coordinateSystem=cc.gcj02towgs84(Mars_coordinateSystem[0],Mars_coordinateSystem[1]) #火星坐标系-->WGS84
                        
                        #更新坐标
                        subData['location']['lat']=WGS84_coordinateSystem[1]
                        subData['detail_info']['lat']=WGS84_coordinateSystem[1]
                        subData['location']['lng']=WGS84_coordinateSystem[0]
                        subData['detail_info']['lng']=WGS84_coordinateSystem[0]  
                        
                        if csv_writer:
                            csv_writer.writerow([subData]) #逐行写入.csv文件
                        jsonDS.append(subData)
            num+=1       
            print("No."+str(num)+" was written to the .csv file.")
    if poi_json:       
        json.dump(jsonDS,poi_json)
        poi_json.write('\n')
        poi_json.close()
    if poi_csv:
        poi_csv.close()
    print("The download is complete.")
    return jsonDS


#位于百度地图POI数据的抓取与地理空间点地图/1. 百度地图POI数据的抓取-单个分类实现与地理空间点地图/1.2 将.csv格式的POI数据转换为pandas的DataFrame
def csv2df(poi_fn_csv):
    import pandas as pd
    from benedict import benedict #benedict库是dict的子类，支持键列表（keylist）/键路径（keypath），应用该库的flatten方法展平嵌套的字典，准备用于DataFrame数据结构
    import csv
    '''function-转换.csv格式的POI数据为pandas的DataFrame'''
    n=0
    with open(poi_fn_csv, newline='',encoding='utf-8') as csvfile:
        poi_reader=csv.reader(csvfile)
        poi_dict={}    
        poiExceptions_dict={}
        for row in poi_reader:    
            if row:
                try:
                    row_benedict=benedict(eval(row[0])) #用eval方法，将字符串字典"{}"转换为字典{}
                    flatten_dict=row_benedict.flatten(separator='_') #展平嵌套字典
                    poi_dict[n]=flatten_dict
                except:                    
                    print("incorrect format of data_row number:%s"%n)                    
                    poiExceptions_dict[n]=row
            n+=1
            #if n==5:break #因为循环次数比较多，在调试代码时，可以设置停止的条件，节省时间与方便数据查看
    poi_df=pd.concat([pd.DataFrame(poi_dict[d_k].values(),index=poi_dict[d_k].keys(),columns=[d_k]).T for d_k in poi_dict.keys()], sort=True,axis=0)
    # print("_"*50)
    for col in poi_df.columns:
        try:
            poi_df[col]=pd.to_numeric(poi_df[col])
        except:
            pass
            #print("%s data type is not converted..."%(col))
    print("_"*50)
    print(".csv to DataFrame is completed!")
    #print(poi_df.head()) #查看最终DataFrame格式下POI数据
    #print(poi_df.dtypes) #查看数据类型
    return poi_df


#位于百度地图POI数据的抓取与地理空间点地图/1.1 多个分类POI爬取|1.2 批量转换.csv格式数据为GeoDataFrame/1.2.1 定义提取文件夹下所有文件路径的函数
def filePath_extraction(dirpath,fileType):
    import os
    '''以所在文件夹路径为键，值为包含该文件夹下所有文件名的列表。文件类型可以自行定义 '''
    filePath_Info={}
    i=0
    for dirpath,dirNames,fileNames in os.walk(dirpath): #os.walk()遍历目录，使用help(os.walk)查看返回值解释
       i+=1
       if fileNames: #仅当文件夹中有文件时才提取
           tempList=[f for f in fileNames if f.split('.')[-1] in fileType]
           if tempList: #剔除文件名列表为空的情况,即文件夹下存在不为指定文件类型的文件时，上一步列表会返回空列表[]
               filePath_Info.setdefault(dirpath,tempList)
    return filePath_Info


#频数分布计算
def frequency_bins(df,bins):
    import pandas as pd
    '''function-频数分布计算'''

    #A-组织数据
    column_name=df.columns[0]
    column_bins_name=df.columns[0]+'_bins'
    df[column_bins_name]=pd.cut(x=df[column_name],bins=bins,right=False) #参数right=False指定为包含左边值，不包括右边值。
    df_bins=df.sort_values(by=[column_name]) #按照分割区间排序
    df_bins.set_index([column_bins_name,df_bins.index],drop=False,inplace=True) #以price_bins和原索引值设置多重索引，同时配置drop=False参数保留原列。
    #print(df_bins.head(10))

    #B-频数计算
    dfBins_frequency=df_bins[column_bins_name].value_counts() #dropna=False  
    dfBins_relativeFrequency=df_bins[column_bins_name].value_counts(normalize=True) #参数normalize=True将计算相对频数(次数) dividing all values by the sum of values
    dfBins_freqANDrelFreq=pd.DataFrame({'fre':dfBins_frequency,'relFre':dfBins_relativeFrequency})
    #print(dfBins_freqANDrelFreq)

    #C-组中值计算
    dfBins_median=df_bins.median(level=0)
    dfBins_median.rename(columns={column_name:'median'},inplace=True)
    #print(dfBins_median)

    #D-合并分割区间、频数计算和组中值的DataFrame格式数据。
    df_fre=dfBins_freqANDrelFreq.join(dfBins_median).sort_index().reset_index() #在合并时会自动匹配index
    #print(ranmen_fre)

    #E-计算频数比例
    df_fre['fre_percent%']=df_fre.apply(lambda row:row['fre']/df_fre.fre.sum()*100,axis=1)

    return df_fre


#convert points .shp to raster 将点数据写入为raster数据。使用raster.SetGeoTransform,栅格化数据。参考GDAL官方代码
def pts2raster(pts_shp,raster_path,cellSize,field_name=False):
    from osgeo import gdal, ogr,osr
    '''
    function - 将.shp格式的点数据转换为.tif栅格(raster)
    
    Paras:
    pts_shp - .shp格式点数据文件路径
    raster_path - 保存的栅格文件路径
    cellSize - 栅格单元大小
    field_name - 写入栅格的.shp点数据属性字段
    '''
    #定义空值（没有数据）的栅格数值 Define NoData value of new raster
    NoData_value=-9999
    
    #打开.shp点数据，并返回地理区域范围 Open the data source and read in the extent
    source_ds=ogr.Open(pts_shp)
    source_layer=source_ds.GetLayer()
    x_min, x_max, y_min, y_max=source_layer.GetExtent()
    
    #使用GDAL库建立栅格 Create the destination data source
    x_res=int((x_max - x_min) / cellSize)
    y_res=int((y_max - y_min) / cellSize)
    target_ds=gdal.GetDriverByName('GTiff').Create(raster_path, x_res, y_res, 1, gdal.GDT_Float64) #gdal的数据类型 gdal.GDT_Float64,gdal.GDT_Int32...
    target_ds.SetGeoTransform((x_min, cellSize, 0, y_max, 0, -cellSize))
    outband=target_ds.GetRasterBand(1)
    outband.SetNoDataValue(NoData_value)

    #向栅格层中写入数据
    if field_name:
        gdal.RasterizeLayer(target_ds,[1], source_layer,options=["ATTRIBUTE={0}".format(field_name)])
    else:
        gdal.RasterizeLayer(target_ds,[1], source_layer,burn_values=[-1])   
        
    #配置投影坐标系统
    spatialRef=source_layer.GetSpatialRef()
    target_ds.SetProjection(spatialRef.ExportToWkt())       
        
    outband.FlushCache()
    return gdal.Open(raster_path).ReadAsArray()


def pts_geoDF2raster(pts_geoDF,raster_path,cellSize,scale):
    from osgeo import gdal,ogr,osr
    import numpy as np
    from scipy import stats
    '''
    function - 将GeoDaraFrame格式的点数据转换为栅格数据
    
    Paras:
    pts_geoDF - GeoDaraFrame格式的点数据
    raster_path - 保存的栅格文件路径
    cellSize - 栅格单元大小
    scale - 缩放核密度估计值
    '''
    #定义空值（没有数据）的栅格数值 Define NoData value of new raster
    NoData_value=-9999
    x_min, y_min,x_max, y_max=pts_geoDF.geometry.total_bounds

    #使用GDAL库建立栅格 Create the destination data source
    x_res=int((x_max - x_min) / cellSize)
    y_res=int((y_max - y_min) / cellSize)
    target_ds=gdal.GetDriverByName('GTiff').Create(raster_path, x_res, y_res, 1, gdal.GDT_Float64 )
    target_ds.SetGeoTransform((x_min, cellSize, 0, y_max, 0, -cellSize))
    outband=target_ds.GetRasterBand(1)
    outband.SetNoDataValue(NoData_value)   
    
    #配置投影坐标系统
    spatialRef = osr.SpatialReference()
    epsg=int(pts_geoDF.crs.srs.split(":")[-1])
    spatialRef.ImportFromEPSG(epsg)  
    target_ds.SetProjection(spatialRef.ExportToWkt())
    
    #向栅格层中写入数据
    #print(x_res,y_res)
    X, Y = np.meshgrid(np.linspace(x_min,x_max,x_res), np.linspace(y_min,y_max,y_res))
    positions=np.vstack([X.ravel(), Y.ravel()])
    values=np.vstack([pts_geoDF.geometry.x, pts_geoDF.geometry.y])    
    print("Start calculating kde...")
    kernel=stats.gaussian_kde(values)
    Z=np.reshape(kernel(positions).T, X.shape)
    print("Finish calculating kde!")
    #print(values)
        
    outband.WriteArray(np.flip(Z,0)*scale)        
    outband.FlushCache()
    print("conversion complete!")
    return gdal.Open(raster_path).ReadAsArray()


def start_time():
    import datetime
    '''
    function-计算当前时间
    '''
    start_time=datetime.datetime.now()
    print("start time:",start_time)
    return start_time

def duration(start_time):
    import datetime
    '''
    function-计算持续时间

    Paras:
    start_time - 开始时间
    '''
    end_time=datetime.datetime.now()
    print("end time:",end_time)
    duration=(end_time-start_time).seconds/60
    print("Total time spend:%.2f minutes"%duration)
    
    
def is_outlier(data,threshold=3.5):
   import numpy as np
   '''
   function-判断异常值

   Params:
   data - 待分析的数据，列表或者一维数组
   threshold - 判断是否为异常值的边界条件    
   '''
   MAD=np.median(abs(data-np.median(data)))
   modified_ZScore=0.6745*(data-np.median(data))/MAD
   #print(modified_ZScore)
   is_outlier_bool=modified_ZScore>threshold    
   return is_outlier_bool,data[~is_outlier_bool]   