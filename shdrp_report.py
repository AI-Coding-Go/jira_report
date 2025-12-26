#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SHDRP项目Jira报表生成器 - 一键生成最近7天报表
"""

import requests
import json
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import os
import subprocess
import platform

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class JiraReportGenerator:
    """Jira报表生成器"""
    
    def __init__(self, jira_url: str, username: str, api_token: str, auth_type: str = "bearer"):
        """初始化Jira连接"""
        self.jira_url = jira_url.rstrip('/')
        self.username = username
        self.api_token = api_token
        self.auth_type = auth_type
        self.board_url = "https://myjira.disney.com/secure/RapidBoard.jspa?rapidView=5588&view=planning.nodetail&selectedIssue=SHDRP-397919&issueLimit=100#"
        self.setup_authentication()
    
    def setup_authentication(self):
        """设置认证方式"""
        if self.auth_type == "bearer":
            self.auth = None
            self.headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
        elif self.auth_type == "basic":
            self.auth = (self.username, self.api_token)
            self.headers = {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
        elif self.auth_type == "pat":
            credentials = f"{self.username}:{self.api_token}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            self.auth = None
            self.headers = {
                "Authorization": f"Basic {encoded_credentials}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
        else:
            raise ValueError(f"不支持的认证类型: {self.auth_type}")
    
    def test_connection(self) -> bool:
        """测试连接是否正常"""
        endpoints = [
            "/rest/api/2/myself",
            "/rest/api/3/myself",
        ]
        
        for endpoint in endpoints:
            url = f"{self.jira_url}{endpoint}"
            try:
                if self.auth:
                    response = requests.get(url, auth=self.auth, headers=self.headers, timeout=10)
                else:
                    response = requests.get(url, headers=self.headers, timeout=10)
                
                if response.status_code == 200:
                    user_info = response.json()
                    logger.info(f"连接成功！用户: {user_info.get('displayName', user_info.get('name', 'Unknown'))}")
                    return True
            except Exception as e:
                logger.debug(f"端点 {endpoint} 测试失败: {e}")
                continue
        
        logger.error("所有认证端点都失败了")
        return False
    
    def search_issues(self, jql: str, fields: List[str] = None) -> Dict:
        """搜索Jira问题"""
        if fields is None:
            fields = ["summary", "status", "assignee", "priority", "created", "updated", 
                     "resolution", "issuetype", "project", "reporter"]
        
        url = f"{self.jira_url}/rest/api/2/search"
        
        params = {
            "jql": jql,
            "fields": ",".join(fields),
            "maxResults": 1000
        }
        
        try:
            if self.auth:
                response = requests.get(url, auth=self.auth, headers=self.headers, params=params, timeout=30)
            else:
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"搜索Jira问题时出错: {e}")
            raise
    
    def get_project_stats(self, project_key: str, days: int = 30, sprint_name: str = None) -> Dict:
        """获取项目统计数据"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 基础JQL查询
        jql = f'project = {project_key} AND created >= "{start_date.strftime("%Y-%m-%d")}"'
        
        # 如果指定了Sprint名称，添加Sprint过滤条件
        if sprint_name:
            jql += f' AND sprint = "{sprint_name}"'
        
        issues_data = self.search_issues(jql)
        issues = issues_data.get("issues", [])
        
        stats = {
            "total_issues": len(issues),
            "by_status": {},
            "by_priority": {},
            "by_assignee": {},
            "by_type": {},
            "by_type_and_status": {},  # 新增：按类型和状态分类
            "resolved": 0,
            "in_progress": 0,
            "todo": 0,
            "recent_issues": [],
            "all_issues": []  # 新增：保存所有问题的详细信息
        }
        
        for issue in issues:
            status = issue["fields"]["status"]["name"]
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            
            priority = issue["fields"].get("priority", {}).get("name", "Unknown")
            stats["by_priority"][priority] = stats["by_priority"].get(priority, 0) + 1
            
            assignee = issue["fields"].get("assignee")
            if assignee:
                assignee_name = assignee["displayName"]
                stats["by_assignee"][assignee_name] = stats["by_assignee"].get(assignee_name, 0) + 1
            
            issue_type = issue["fields"]["issuetype"]["name"]
            stats["by_type"][issue_type] = stats["by_type"].get(issue_type, 0) + 1
            
            # 按类型和状态分类统计
            if issue_type not in stats["by_type_and_status"]:
                stats["by_type_and_status"][issue_type] = {}
            stats["by_type_and_status"][issue_type][status] = stats["by_type_and_status"][issue_type].get(status, 0) + 1
            
            if status.lower() in ["done", "completed", "closed", "resolved"]:
                stats["resolved"] += 1
            elif status.lower() in ["in progress", "development", "code review"]:
                stats["in_progress"] += 1
            else:
                stats["todo"] += 1
            
            # 保存所有问题的详细信息
            issue_url = f"{self.jira_url}/browse/{issue['key']}"
            issue_info = {
                "key": issue["key"],
                "summary": issue["fields"]["summary"],
                "status": status,
                "assignee": assignee["displayName"] if assignee else "未分配",
                "priority": priority,
                "type": issue_type,
                "url": issue_url
            }
            stats["all_issues"].append(issue_info)
            
            if len(stats["recent_issues"]) < 10:
                stats["recent_issues"].append(issue_info)
        
        return stats
    
    def create_markdown_report(self, jira_data: Dict, project_name: str, days: int) -> str:
        """创建Markdown格式的报表"""
        current_date = datetime.now()
        month_name = current_date.strftime("%B %Y")
        
        markdown_content = f"""Hi all Studio Incredible, Studio Moana and Studio Castalia team members, RMs and managers,

Here is a monthly report from Studio Incredible, Studio Moana and Studio Castalia sustainment teams.
You can refer to SHDR Studio Incredible + Studio Moana + Studio Castalia Sustainment Dashboard for more details.
Thank you.

{month_name} Monthly Sustainment Report

Studio Incredible, Studio Moana, Studio Castalia

Sprints

Sprint 371 & Sprint 372

Statistics JIRA Tickets

Story, Bug, and Security

Completed JIRA Ticket Status

{self._generate_completed_status_table(jira_data)}

{self._generate_type_summary_table(jira_data)}

---
*Report generated on {current_date.strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        return markdown_content
    
    def create_sprint_markdown_report(self, jira_data: Dict, studio_name: str, sprint_name: str, days: int) -> str:
        """创建Sprint特定的Markdown格式报表"""
        current_date = datetime.now()
        month_name = current_date.strftime("%B %Y")
        
        markdown_content = f"""Hi all {studio_name} team members, RMs and managers,

Here is a monthly report from {studio_name} sustainment team.
You can refer to {studio_name} Sustainment Dashboard for more details.
Thank you.

{month_name} Monthly Sustainment Report

{studio_name}

Sprints

Sprint {sprint_name}

Statistics JIRA Tickets

Story, Bug, and Security

Completed JIRA Ticket Status

{self._generate_completed_status_table(jira_data)}

{self._generate_type_summary_table(jira_data)}

All JIRA Tickets by Status

{self._generate_all_status_table(jira_data)}

JIRA Tickets Details (JIRA ID, Assignee, Status, Type)

{self._generate_detailed_issues_table(jira_data)}

---
*Report generated on {current_date.strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        return markdown_content
    
    def _calculate_completion_rate(self, jira_data: Dict) -> float:
        """计算完成率"""
        total = jira_data.get('total_issues', 0)
        if total == 0:
            return 0.0
        resolved = jira_data.get('resolved', 0)
        return (resolved / total) * 100
    
    def _generate_status_table(self, status_data: Dict, total: int) -> str:
        """生成状态表格Markdown"""
        rows = []
        for status, count in sorted(status_data.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total * 100) if total > 0 else 0
            status_emoji = self._get_status_emoji(status)
            rows.append(f"| {status_emoji} {status} | {count} | {percentage:.1f}% |")
        return "\n".join(rows)
    
    def _generate_priority_table(self, priority_data: Dict, total: int) -> str:
        """生成优先级表格Markdown"""
        rows = []
        priority_order = ["Highest", "High", "Medium", "Low", "Lowest"]
        
        for priority in priority_order:
            if priority in priority_data:
                count = priority_data[priority]
                percentage = (count / total * 100) if total > 0 else 0
                priority_emoji = self._get_priority_emoji(priority)
                rows.append(f"| {priority_emoji} {priority} | {count} | {percentage:.1f}% |")
        
        for priority, count in priority_data.items():
            if priority not in priority_order:
                percentage = (count / total * 100) if total > 0 else 0
                rows.append(f"| 📌 {priority} | {count} | {percentage:.1f}% |")
        
        return "\n".join(rows)
    
    def _generate_assignee_table(self, assignee_data: Dict) -> str:
        """生成负责人表格Markdown"""
        rows = []
        for assignee, count in sorted(assignee_data.items(), key=lambda x: x[1], reverse=True):
            rows.append(f"| 👤 {assignee} | {count} |")
        return "\n".join(rows)
    
    def _generate_type_table(self, type_data: Dict, total: int) -> str:
        """生成类型表格Markdown"""
        rows = []
        for issue_type, count in sorted(type_data.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total * 100) if total > 0 else 0
            type_emoji = self._get_type_emoji(issue_type)
            rows.append(f"| {type_emoji} {issue_type} | {count} | {percentage:.1f}% |")
        return "\n".join(rows)
    
    def _generate_recent_issues_table(self, recent_issues: List[Dict]) -> str:
        """生成最近问题表格Markdown"""
        rows = []
        for issue in recent_issues:
            key = issue["key"]
            summary = issue["summary"][:50] + "..." if len(issue["summary"]) > 50 else issue["summary"]
            status = issue["status"]
            assignee = issue["assignee"]
            priority = issue["priority"]
            url = issue["url"]
            
            rows.append(f"| [{key}]({url}) | {summary} | {status} | {assignee} | {priority} |")
        
        return "\n".join(rows)
    
    def _get_status_emoji(self, status: str) -> str:
        """获取状态对应的emoji"""
        status_lower = status.lower()
        if status_lower in ["done", "completed", "closed", "resolved"]:
            return "✅"
        elif status_lower in ["in progress", "development", "code review"]:
            return "🔄"
        elif status_lower in ["to do", "open", "new"]:
            return "⏳"
        elif status_lower in ["blocked", "on hold"]:
            return "🚫"
        else:
            return "📋"
    
    def _get_priority_emoji(self, priority: str) -> str:
        """获取优先级对应的emoji"""
        priority_lower = priority.lower()
        if priority_lower in ["highest", "critical"]:
            return "🔴"
        elif priority_lower in ["high", "major"]:
            return "🟠"
        elif priority_lower in ["medium", "normal"]:
            return "🟡"
        elif priority_lower in ["low", "minor"]:
            return "🟢"
        elif priority_lower in ["lowest", "trivial"]:
            return "🔵"
        else:
            return "📌"
    
    def _get_type_emoji(self, issue_type: str) -> str:
        """获取问题类型对应的emoji"""
        type_lower = issue_type.lower()
        if "bug" in type_lower:
            return "🐛"
        elif "story" in type_lower:
            return "📖"
        elif "task" in type_lower:
            return "📝"
        elif "epic" in type_lower:
            return "🏗️"
        elif "sub-task" in type_lower:
            return "🔨"
        elif "improvement" in type_lower:
            return "⚡"
        elif "feature" in type_lower:
            return "✨"
        else:
            return "📋"
    
    def _generate_completed_status_table(self, jira_data: Dict) -> str:
        """生成已完成状态表格"""
        completed_statuses = ["Resolved", "Closed", "In Review", "Verified in Latest", "Rejected"]
        by_status = jira_data.get('by_status', {})
        
        rows = []
        total_completed = 0
        
        for status in completed_statuses:
            count = by_status.get(status, 0)
            total_completed += count
            rows.append(f"| {status} | {count} |")
        
        rows.append(f"| **Total Completed** | **{total_completed}** |")
        
        return "\n".join([
            "| Status | Count |",
            "|--------|-------|",
            "\n".join(rows)
        ])
    
    def _generate_type_summary_table(self, jira_data: Dict) -> str:
        """按类型汇总已完成的问题"""
        by_type_and_status = jira_data.get('by_type_and_status', {})
        completed_statuses = ["Resolved", "Closed", "In Review", "Verified in Latest", "Rejected"]
        
        rows = []
        total_by_type = {}
        
        # 统计每种类型的已完成数量
        for issue_type, status_dict in by_type_and_status.items():
            completed_count = 0
            for status in completed_statuses:
                completed_count += status_dict.get(status, 0)
            total_by_type[issue_type] = completed_count
        
        # 按完成数量排序
        for issue_type, completed_count in sorted(total_by_type.items(), key=lambda x: x[1], reverse=True):
            type_emoji = self._get_type_emoji(issue_type)
            rows.append(f"| {type_emoji} {issue_type} | {completed_count} |")
        
        return "\n".join([
            "Completed Story, Bug, and Security by Type",
            "",
            "| Type | Completed Count |",
            "|------|-----------------|",
            "\n".join(rows)
        ])
    
    def _generate_all_status_table(self, jira_data: Dict) -> str:
        """生成所有状态的统计表格"""
        by_status = jira_data.get('by_status', {})
        
        rows = []
        for status, count in sorted(by_status.items(), key=lambda x: x[1], reverse=True):
            status_emoji = self._get_status_emoji(status)
            rows.append(f"| {status_emoji} {status} | {count} |")
        
        return "\n".join([
            "| Status | Count |",
            "|--------|-------|",
            "\n".join(rows)
        ])
    
    def _generate_detailed_issues_table(self, jira_data: Dict) -> str:
        """生成详细的问题列表表格"""
        all_issues = jira_data.get('all_issues', [])
        
        # 按状态和优先级排序
        def sort_key(issue):
            status_priority = {
                "Resolved": 1, "Closed": 1, "Verified in Latest": 1,
                "In Review": 2, "In Progress": 3, "In Dev": 3,
                "Open": 4, "New": 4, "To Do": 4,
                "Blocked": 5, "Rejected": 6
            }
            priority_order = {"Highest": 1, "High": 2, "Medium": 3, "Low": 4, "Lowest": 5}
            
            status_score = status_priority.get(issue["status"], 10)
            priority_score = priority_order.get(issue["priority"], 3)
            
            return (status_score, priority_score, issue["key"])
        
        sorted_issues = sorted(all_issues, key=sort_key)
        
        rows = []
        for issue in sorted_issues:
            key = issue["key"]
            assignee = issue["assignee"]
            status = issue["status"]
            issue_type = issue["type"]
            type_emoji = self._get_type_emoji(issue_type)
            
            rows.append(f"| [{key}]({issue['url']}) | {assignee} | {status} | {type_emoji} {issue_type} |")
        
        return "\n".join([
            "| JIRA ID | Assignee | Status | Type |",
            "|---------|----------|--------|------|",
            "\n".join(rows)
        ])
    
    def _generate_recommendations(self, jira_data: Dict, completion_rate: float) -> str:
        """生成建议"""
        recommendations = []
        
        if completion_rate < 30:
            recommendations.append("- ⚠️ 完成率较低，建议关注项目进度和资源分配")
        elif completion_rate > 80:
            recommendations.append("- 🎉 项目进展良好，保持当前节奏")
        
        if jira_data.get('todo', 0) > jira_data.get('in_progress', 0) * 2:
            recommendations.append("- 📋 待处理问题较多，建议加快任务分配")
        
        if jira_data.get('in_progress', 0) > 10:
            recommendations.append("- 🔄 进行中任务较多，建议关注瓶颈问题")
        
        high_priority_count = sum(1 for priority in jira_data.get('by_priority', {}).keys() 
                                 if priority.lower() in ['highest', 'high'])
        if high_priority_count > 5:
            recommendations.append("- 🔴 高优先级问题较多，建议优先处理")
        
        if not recommendations:
            recommendations.append("- ✅ 项目状态良好，继续保持")
        
        return "\n".join(recommendations)
    
    def save_report(self, content: str, filename: str, output_dir: str = "reports") -> str:
        """保存报表到文件"""
        os.makedirs(output_dir, exist_ok=True)
        
        # 如果filename没有.md扩展名，则添加
        if not filename.endswith('.md'):
            filename += '.md'
            
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"报表已保存到: {filepath}")
        return filepath

def generate_sprint_report(jira_client, project_key, sprint_name, studio_name, days=30):
    """生成特定Sprint的报表"""
    print(f"🚀 生成 {studio_name} {sprint_name} 报表")
    print("="*50)
    
    print(f"📊 项目: {project_key}")
    print(f"📅 统计: 最近 {days} 天")
    print(f"🏃 Sprint: {sprint_name}")
    print(f"🔗 Board: {jira_client.board_url}")
    
    try:
        # 测试连接
        if not jira_client.test_connection():
            print("❌ 连接失败")
            return None
        
        # 获取数据，包含Sprint过滤
        jira_data = jira_client.get_project_stats(project_key, days, sprint_name)
        
        # 生成报表
        markdown_content = jira_client.create_sprint_markdown_report(jira_data, studio_name, sprint_name, days)
        
        # 保存报表
        filename = f"sprint_{sprint_name}_{project_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = jira_client.save_report(markdown_content, filename, "reports")
        
        print(f"\n🎉 报表生成成功！")
        print(f"📁 文件: {filepath}")
        
        # 显示关键统计信息
        print("\n📊 关键统计:")
        lines = markdown_content.split('\n')
        for line in lines:
            if "Total Completed" in line:
                print(f"   {line.strip()}")
        
        # 自动打开文件
        try:
            if platform.system() == "Darwin":  # macOS
                subprocess.run(["open", filepath])
            elif platform.system() == "Windows":
                subprocess.run(["start", filepath], shell=True)
            else:  # Linux
                subprocess.run(["xdg-open", filepath])
            print("\n✅ 报表已自动打开")
        except Exception as e:
            print(f"\n❌ 自动打开失败: {e}")
            print(f"请手动打开: {filepath}")
        
        return filepath
        
    except Exception as e:
        print(f"❌ 生成报表失败: {e}")
        return None

def main():
    """主函数 - 生成Sprint 374报表"""
    print("🚀 生成Sprint 374报表")
    print("="*50)
    
    # 加载配置
    try:
        with open('fixed_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("❌ 配置文件不存在")
        return
    
    # 创建Jira客户端
    jira_client = JiraReportGenerator(
        jira_url=config['jira']['url'],
        username=config['jira']['username'],
        api_token=config['jira']['api_token'],
        auth_type=config['jira'].get('auth_type', 'bearer')
    )
    
    # 生成Sprint 374报表
    projects = [
        {
            "project_key": "SHDRP",        # 使用已知存在的项目键
            "sprint_name": "SHDR Android Sustainment 374",
            "studio_name": "SHDR Android Sustainment"
        }
    ]
    
    generated_files = []
    
    for project in projects:
        print(f"\n{'='*60}")
        filepath = generate_sprint_report(
            jira_client, 
            project["project_key"], 
            project["sprint_name"], 
            project["studio_name"],
            days=30  # 月度报表，统计30天
        )
        if filepath:
            generated_files.append(filepath)
    
    print(f"\n🎉 所有报表生成完成！")
    print(f"📁 共生成 {len(generated_files)} 个报表文件:")
    for i, filepath in enumerate(generated_files, 1):
        print(f"   {i}. {filepath}")

if __name__ == "__main__":
    main()