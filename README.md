# Jira报表自动化系统

这是一个完整的 Python脚本，用于从Jira获取报表数据并生成 MarkDown 文档, 生成目录在 \reports 下面。

## 功能特性

- 🔗 **Jira API集成**: 支持JQL查询，获取项目统计数据
- 📊 **数据可视化**: 生成美观的HTML格式报表
- 📧 **邮件发送**: 通过Outlook SMTP发送报表邮件
- ⚙️ **灵活配置**: 支持多项目、多收件人配置
- 📈 **统计分析**: 按状态、优先级、负责人等维度统计
- 🎨 **响应式设计**: HTML报表支持移动端查看

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置说明

### 1. Jira配置

1. 获取Jira API Token:
   - 登录Atlassian账户
   - 访问 https://id.atlassian.com/manage-profile/security/api-tokens
   - 创建新的API Token

2. 配置Jira连接信息:
   ```json
   {
       "jira": {
           "url": "https://your-company.atlassian.net",
           "username": "your-email@company.com",
           "api_token": "your-api-token"
       }
   }
   ```


## 使用方法

### 基本用法

```python
from jira_report_automation import JiraReportAutomation

# 配置
config = {
    'jira': {
        'url': 'https://your-company.atlassian.net',
        'username': 'your-email@company.com',
        'api_token': 'your-api-token'
    }
}

# 创建自动化实例
automation = JiraReportAutomation(config)

```

### 命令行运行

```bash
python shdr_report.py
```

### 使用配置文件

```python
import json

# 加载配置
with open('config.json', 'r') as f:
    config = json.load(f)

automation = JiraReportAutomation(config)

# 批量发送报表
for report_config in config['reports']:
    if report_config['enabled']:
        automation.generate_and_send_report(
            project_key=report_config['project_key'],
            recipients=report_config['recipients'],
            days=report_config['days']
        )
```

## 报表内容

生成的HTML报表包含以下内容：

1. **概览统计**
   - 总问题数
   - 已完成数量
   - 进行中数量
   - 待处理数量

2. **完成进度**
   - 可视化进度条
   - 完成率百分比

3. **详细分析**
   - 按状态分布
   - 按优先级分布
   - 按负责人分布

4. **响应式设计**
   - 支持桌面和移动端
   - 现代化UI设计

## 高级功能

### 自定义JQL查询

```python
# 获取特定Sprint的数据
jql = "project = PROJ AND sprint = 'Sprint 23'"
issues = jira_client.search_issues(jql)

# 获取高优先级未解决问题
jql = "project = PROJ AND priority in (High, Highest) AND status not in (Done, Closed)"
urgent_issues = jira_client.search_issues(jql)
```

### 添加附件

```python
# 生成图表并添加为附件
import matplotlib.pyplot as plt

# 创建图表
plt.figure(figsize=(10, 6))
# ... 绘图代码 ...

# 保存图表
chart_path = 'project_chart.png'
plt.savefig(chart_path)

# 发送邮件时添加附件
email_sender.send_email(
    recipients=recipients,
    subject="项目报表",
    html_content=html_content,
    attachments=[chart_path]
)
```

### 定时任务

使用cron或Windows任务计划程序设置定时执行：

```bash
```

## 故障排除

### 常见问题

1. **Jira认证失败**
   - 检查API Token是否正确
   - 确认用户名格式（邮箱）
   - 验证Jira URL是否正确

2**数据获取异常**
   - 验证项目键是否正确
   - 检查JQL查询语法
   - 确认用户权限

### 调试模式

启用详细日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 安全注意事项

1. **敏感信息保护**
   - 不要将API Token和密码提交到版本控制
   - 使用环境变量或配置文件
   - 定期更换API Token

2. **权限最小化**
   - 使用专用服务账户
   - 仅授予必要的Jira权限

## 扩展开发

### 添加新的统计维度

```python
def get_custom_stats(self, project_key: str) -> Dict:
    """自定义统计逻辑"""
    # 实现自定义统计
    pass
```

### 集成其他邮件服务

```python
class GmailEmailSender(OutlookEmailSender):
    """Gmail邮件发送器"""
    
    def __init__(self, email: str, password: str):
        super().__init__(
            smtp_server='smtp.gmail.com',
            smtp_port=587,
            email=email,
            password=password
        )
```

## 许可证

MIT License

## 支持

如有问题或建议，请联系系统管理员。