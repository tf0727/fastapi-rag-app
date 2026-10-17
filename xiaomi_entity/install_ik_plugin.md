# 安装 IK 中文分词插件

## Docker 环境安装（推荐）

### 1. 进入 Elasticsearch 容器
```bash
# 查看运行中的容器
docker ps

# 进入容器（替换 container_id 为你的容器ID或名称）
docker exec -it <container_id> bash
```

### 2. 安装 IK 插件
```bash
# 在容器内执行
./bin/elasticsearch-plugin install https://github.com/medcl/elasticsearch-analysis-ik/releases/download/v7.17.9/elasticsearch-analysis-ik-7.17.9.zip

# 如果是 ES 8.x，使用对应版本
./bin/elasticsearch-plugin install https://github.com/medcl/elasticsearch-analysis-ik/releases/download/v8.11.0/elasticsearch-analysis-ik-8.11.0.zip
```

### 3. 退出容器并重启
```bash
exit
docker restart <container_id>
```

### 4. 验证安装
```bash
# 等待容器启动完成（约30秒）
# 测试 IK 分词器
curl -X POST "http://localhost:9200/_analyze" -H 'Content-Type: application/json' -d'
{
  "analyzer": "ik_smart",
  "text": "小米智能手机"
}
'
```

## 非 Docker 环境安装

### Windows
```bash
# 进入 Elasticsearch 安装目录
cd C:\elasticsearch-7.17.9

# 安装插件
.\bin\elasticsearch-plugin install https://github.com/medcl/elasticsearch-analysis-ik/releases/download/v7.17.9/elasticsearch-analysis-ik-7.17.9.zip

# 重启服务
```

### Linux/Mac
```bash
# 进入 Elasticsearch 安装目录
cd /path/to/elasticsearch

# 安装插件
./bin/elasticsearch-plugin install https://github.com/medcl/elasticsearch-analysis-ik/releases/download/v7.17.9/elasticsearch-analysis-ik-7.17.9.zip

# 重启服务
sudo systemctl restart elasticsearch
```

## 查看已安装插件
```bash
# 方法1：命令行
./bin/elasticsearch-plugin list

# 方法2：API
curl http://localhost:9200/_cat/plugins
```

