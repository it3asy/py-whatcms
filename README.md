# 一、关于whatcms
----------------


## 适用场景
适用于针对批量网站快速识别网站CMS信息.


## CMS识别方式

* 网站特定页面特征关键字;
* 网站内部链接特征URL.
	> 只提取指定页面的链接进行特征URL匹配.

## CMS识别过程

 " **枚举CMS** -> **枚举识别规则** -> **请求URL** -> **匹配识别规则** " 

## 运行过程
* 通过pickle序列化/反序列实现缓存HTTP请求，避免多个规则访问同一URL时产生多次请求。

## 配置文件解析
### software
Softwate段用来存放CMS信息,主要字段有：

* **name**: CMS名称
* **platform**: 服务端语言

### whatcms-X

whatcms-X用来存放CMS识别规则(X={1,2,3,4,...})。规则根据识别方式分为两种，特征关键字方式对应type=html，特征URL对应type=url。

* **url**: 指定URL
* **type**：指定识别方式，html表示特征关键字方式，url表示特征url方式.
* **partner**: 预留字段，与指定规则协同.
* **rank**: 预留字段，规则权值，默认为1.
* **key.position**: 关键字位置,默认为空.
	* 当type=html时:
		* title: 匹配的位置为页面标题,
		* meta: 匹配的位置为页面meta标签,
	* 当type=url时：
		* urlparse.path：匹配的位置为urlparse解析后的path字段.
* **key.words**: 关键字内容.
* **key.split**: 多个关键字的时候指定关键字分隔符.
* **key.logic**: 多个关键字之间匹配结果关系,and或in,默认为in.
* **function**: 执行关键字匹配的函数,支持re.search和in.
* **flags**: 可选字段，当函数为re.search时的flags参数值.
* **ignorecase**: 可选字段，当函数为in时是否忽略大小写,1忽略,0不忽略.


<hr>

# 二、关于CMS识别
----------------------

## 制做CMS识别工具

通常 **CMS识别程序 = 规则 + 规则解释器**，因而制做一个强大的CMS识别程序可分解为两部分工作：

1） 制作维护一个精准庞大规则库

2） 编写一个强大的规则解释器



## 一些CMS识别工具


