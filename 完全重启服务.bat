@echo off
chcp 65001 >nul
echo ========================================
echo   完全重启服务（清除缓存和旧数据）
echo ========================================
echo.

echo [步骤 1/7] 停止Flask服务...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq 医疗隐私保护系统*" 2>nul
timeout /t 2 /nobreak >nul
echo ✓ Flask服务已停止

echo.
echo [步骤 2/7] 清除Python字节码缓存...
echo 删除 services\__pycache__\*.pyc
del /q services\__pycache__\*.pyc 2>nul
echo ✓ 字节码缓存已清除

echo.
echo [步骤 3/7] 删除旧的输出文件...
if exist output\ (
    echo 删除 output\ 目录...
    rd /s /q output 2>nul
    echo ✓ 旧输出文件已删除
) else (
    echo ○ 输出目录不存在，跳过
)

echo.
echo [步骤 4/7] 删除旧的存储数据库...
if exist storage_repo\db\index.sqlite (
    echo 删除数据库文件...
    del /q storage_repo\db\index.sqlite 2>nul
    echo ✓ 数据库已删除
) else (
    echo ○ 数据库不存在，跳过
)

if exist storage_repo\cas\ (
    echo 删除CAS存储...
    rd /s /q storage_repo\cas 2>nul
    echo ✓ CAS存储已删除
) else (
    echo ○ CAS目录不存在，跳过
)

if exist storage_repo\batches\ (
    echo 删除批次目录...
    rd /s /q storage_repo\batches 2>nul
    echo ✓ 批次目录已删除
) else (
    echo ○ 批次目录不存在，跳过
)

echo.
echo [步骤 5/7] 重新创建必要的目录...
mkdir output 2>nul
mkdir storage_repo\db 2>nul
mkdir storage_repo\cas 2>nul
mkdir storage_repo\batches 2>nul
echo ✓ 目录已创建

echo.
echo [步骤 6/7] 等待2秒...
timeout /t 2 /nobreak >nul
echo ✓ 完成

echo.
echo [步骤 7/7] 启动Flask服务...
echo.
echo ========================================
echo   服务启动中...
echo ========================================
echo.
start "医疗隐私保护系统 - Flask Server" cmd /k "python app.py --port 5000"
timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo   ✅ 服务已重启
echo ========================================
echo.
echo 新窗口已打开Flask服务
echo 请访问: http://127.0.0.1:5000
echo.
echo ⚠️  重要说明:
echo   1. 数据库和缓存已完全清空
echo   2. 请刷新浏览器（Ctrl+Shift+R）
echo   3. 或使用无痕模式测试
echo.
echo ========================================
echo   测试步骤:
echo ========================================
echo.
echo 【测试批量处理】
echo   1. 点击"批量检测"标签
echo   2. 选择CSV文件夹和DICOM文件夹
echo   3. 点击"批量上传并检测"
echo   4. 等待检测完成
echo   5. 点击"执行保护"
echo   6. 点击"存储入库"
echo   7. 点击"查看存储"
echo   8. 应该看到存储的对象列表
echo.
echo 【测试单文件处理】
echo   1. 点击"单文件检测"标签
echo   2. 选择CSV文件和DICOM文件
echo   3. 点击"上传并检测"
echo   4. 等待检测完成
echo   5. 点击"执行保护"（应该不再报错）
echo   6. 点击"存储入库"
echo   7. 点击"查看存储"
echo   8. 应该看到存储的对象
echo.
pause

