mkdir -p ~/s3-test && cd ~/s3-test

cat > Dockerfile << 'EOF'
FROM amazon/aws-cli:latest

COPY test.sh /test.sh
RUN chmod +x /test.sh

ENTRYPOINT ["/test.sh"]
EOF


cat > test.sh << 'SCRIPT'
#!/bin/bash

BUCKET="你的S3桶名"
TEST_FILE="s3-test/test.txt"

echo "===== S3 权限测试开始 ====="
echo "时间: $(date)"
echo "桶名: ${BUCKET}"
echo ""

# 1. PutObject
echo "[1] 测试 PutObject（上传）..."
echo "hello from fargate $(date)" > /tmp/test.txt
aws s3 cp /tmp/test.txt s3://${BUCKET}/${TEST_FILE} 2>&1
if [ $? -eq 0 ]; then echo "  ✅ PutObject 成功"; else echo "  ❌ PutObject 失败"; fi
echo ""

# 2. ListBucket
echo "[2] 测试 ListBucket（列出）..."
aws s3 ls s3://${BUCKET}/s3-test/ 2>&1
if [ $? -eq 0 ]; then echo "  ✅ ListBucket 成功"; else echo "  ❌ ListBucket 失败"; fi
echo ""

# 3. GetObject
echo "[3] 测试 GetObject（下载）..."
aws s3 cp s3://${BUCKET}/${TEST_FILE} /tmp/downloaded.txt 2>&1
if [ $? -eq 0 ]; then
  echo "  ✅ GetObject 成功"
  echo "  文件内容: $(cat /tmp/downloaded.txt)"
else
  echo "  ❌ GetObject 失败"
fi
echo ""

# 4. DeleteObject
echo "[4] 测试 DeleteObject（删除）..."
aws s3 rm s3://${BUCKET}/${TEST_FILE} 2>&1
if [ $? -eq 0 ]; then echo "  ✅ DeleteObject 成功"; else echo "  ❌ DeleteObject 失败"; fi
echo ""

# 5. 确认
echo "[5] 确认文件已删除..."
RESULT=$(aws s3 ls s3://${BUCKET}/s3-test/ 2>&1)
if [ -z "$RESULT" ]; then
  echo "  ✅ 文件确认已删除"
else
  echo "  文件列表: $RESULT"
fi

echo ""
echo "===== S3 权限测试完成 ====="

# 保持容器运行30秒，确保日志全部推送到CloudWatch
echo "等待30秒确保日志推送完成..."
sleep 30
echo "测试容器退出"
SCRIPT