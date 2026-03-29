#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
心理咨询模块 - 集成EmoLLM
"""

from flask import Blueprint, request, jsonify, session, render_template, redirect
from utils.emollm_client import get_emollm_client
from utils import db
import logging
import datetime
import time
from new_features.assessment_context.service import (
    build_assessment_context,
    get_assessment_payload,
    get_latest_assessment_payload,
)

try:
    from new_features.skill_router.base import SkillContext
    from new_features.skill_router.router import get_skill_router
except Exception:  # pragma: no cover - keep legacy flow safe if optional module fails
    SkillContext = None
    get_skill_router = None

# 配置日志
logger = logging.getLogger(__name__)

# 创建蓝图
pc = Blueprint("psychological_counseling", __name__)
skill_router = get_skill_router() if get_skill_router else None


@pc.route('/api/chat', methods=['POST'])
def chat():
    """
    心理咨询聊天接口（支持流式输出）
    
    Request Body:
        {
            "message": "用户消息",
            "include_emotion": true/false,  # 是否包含情绪上下文
            "history": [],  # 可选的历史对话
            "stream": true  # 是否流式输出
        }
    
    Response:
        如果stream=true，返回SSE流式响应
        否则返回JSON响应
    """
    try:
        # 获取请求数据
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({
                'status': 'error',
                'message': '请提供消息内容'
            }), 400
        
        user_message = data['message']
        include_emotion = data.get('include_emotion', False)
        history = data.get('history', [])
        stream = data.get('stream', True)  # 默认启用流式输出
        web_search = data.get('web_search', False)  # 获取前端的搜索开关状态
        assessment_context = data.get('assessment_context')
        include_report = data.get('include_report', False)
        report_record_id = _parse_optional_int(data.get('report_record_id'))

        # 获取用户信息
        userinfo = session.get('userinfo', {})
        user_id = userinfo.get('id')
        user_role = userinfo.get('role')
        username = userinfo.get('username') or userinfo.get('name') or 'unknown'

        if include_report and not assessment_context:
            assessment_context = _build_request_assessment_context(
                user_id=user_id,
                user_role=user_role,
                username=username,
                report_record_id=report_record_id,
            )
        
        # 打印用户消息到终端
        print(f"\n{'='*60}")
        print(f"[用户消息] {username}: {user_message[:200]}...")
        print(f"{'='*60}\n")
        logger.info(f"[用户消息] {username}: {user_message[:50]}...")
        
        # 构建情绪上下文（如果需要）
        emotion_context = None
        if include_emotion:
            emotion_context = _get_user_emotion_context(username)
        
        skill_result = _try_route_chat_skill(
            username=username,
            user_message=user_message,
            history=history,
            include_emotion=include_emotion,
            emotion_context=emotion_context,
            stream=stream,
            web_search=web_search,
            request_payload=data,
        )
        if skill_result:
            response_text = skill_result['response_text']
            skill_name = skill_result['skill_name']
            store_emotion_context = skill_result.get('emotion_context')

            if skill_result.get('should_store', True):
                _save_chat_record(username, user_message, response_text, store_emotion_context)

            if stream:
                from flask import Response
                import json as json_lib

                def generate_skill_response():
                    for chunk in _iter_stream_chunks(response_text):
                        yield f"data: {json_lib.dumps({'chunk': chunk, 'done': False}, ensure_ascii=False)}\n\n"
                        time.sleep(0.02)
                    yield f"data: {json_lib.dumps({'chunk': '', 'done': True, 'full_response': response_text}, ensure_ascii=False)}\n\n"
                    print(f"\n{'='*60}")
                    print(f"[Skill:{skill_name}] {username}: {response_text}")
                    print(f"{'='*60}\n")
                    logger.info("[Skill:%s] %s: %s...", skill_name, username, response_text[:100])

                return Response(generate_skill_response(), mimetype='text/event-stream')

            print(f"\n{'='*60}")
            print(f"[Skill:{skill_name}] {username}: {response_text}")
            print(f"{'='*60}\n")
            logger.info("[Skill:%s] %s: %s...", skill_name, username, response_text[:100])

            return jsonify({
                'status': 'success',
                'response': response_text,
                'history': history,
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'emotion_included': include_emotion
            })

        # 调用EmoLLM
        logger.info(f"用户 {username} 发起咨询: {user_message[:50]}... (流式: {stream}, 联网搜索: {web_search})")
        
        emollm_client = get_emollm_client()
        # 如果消息很长（包含报告数据），增加超时时间
        # 流式请求需要更长的超时时间，因为需要持续读取数据流
        timeout = 180 if len(user_message) > 1000 else 120  # 流式请求默认120秒，长消息180秒
        
        if stream:
            # 流式输出
            from flask import Response
            import json as json_lib
            
            def generate():
                full_response = ""
                try:
                    # 调用流式API，传入 enable_web_search
                    for event in emollm_client.chat_stream(
                        prompt=user_message,
                        history=history,
                        emotion_context=emotion_context,
                        assessment_context=assessment_context,
                        max_length=4096,
                        temperature=0.8,
                        enable_web_search=web_search,
                        timeout=timeout
                    ):
                        if not event:
                            continue

                        if isinstance(event, dict):
                            if event.get('chunk'):
                                full_response += event['chunk']
                            if event.get('replace_full_response'):
                                full_response = event['replace_full_response']
                            yield f"data: {json_lib.dumps(event, ensure_ascii=False)}\n\n"
                            continue

                        full_response += event
                        # 发送SSE格式的数据
                        yield f"data: {json_lib.dumps({'chunk': event, 'done': False}, ensure_ascii=False)}\n\n"
                    
                    # 流式输出完成
                    yield f"data: {json_lib.dumps({'chunk': '', 'done': True, 'full_response': full_response}, ensure_ascii=False)}\n\n"
                    
                    # 打印AI回复到终端
                    print(f"\n{'='*60}")
                    print(f"[AI回复] {username}: {full_response}")
                    print(f"{'='*60}\n")
                    logger.info(f"[AI回复] {username}: {full_response[:100]}...")
                    
                    # 保存对话记录到数据库
                    _save_chat_record(username, user_message, full_response, emotion_context)
                    
                except Exception as e:
                    error_msg = str(e)
                    print(f"\n{'='*60}")
                    print(f"[AI调用失败] {username}: {error_msg}")
                    print(f"{'='*60}\n")
                    logger.error(f"[AI调用失败] {username}: {error_msg}", exc_info=True)
                    yield f"data: {json_lib.dumps({'error': error_msg, 'done': True}, ensure_ascii=False)}\n\n"
            
            return Response(generate(), mimetype='text/event-stream')
        else:
            # 非流式输出（兼容旧代码）
            try:
                response, updated_history = emollm_client.chat(
                    prompt=user_message,
                    history=history,
                    emotion_context=emotion_context,
                    assessment_context=assessment_context,
                    max_length=4096,
                    temperature=0.8,
                    enable_web_search=web_search,
                    timeout=timeout
                )
                
                # 打印AI回复到终端
                print(f"\n{'='*60}")
                print(f"[AI回复] {username}: {response}")
                print(f"{'='*60}\n")
                logger.info(f"[AI回复] {username}: {response[:100]}...")
                
                # 保存对话记录到数据库
                _save_chat_record(username, user_message, response, emotion_context)
                
                return jsonify({
                    'status': 'success',
                    'response': response,
                    'history': updated_history,
                    'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'emotion_included': include_emotion
                })
            except Exception as e:
                error_msg = str(e)
                print(f"\n{'='*60}")
                print(f"[AI调用失败] {username}: {error_msg}")
                print(f"{'='*60}\n")
                logger.error(f"[AI调用失败] {username}: {error_msg}", exc_info=True)
                return jsonify({
                    'status': 'error',
                    'message': f'服务异常: {error_msg}'
                }), 500
        
    except Exception as e:
        error_msg = str(e)
        print(f"\n{'='*60}")
        print(f"[聊天接口异常] {error_msg}")
        print(f"{'='*60}\n")
        logger.error(f"心理咨询异常: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'服务异常: {error_msg}'
        }), 500


@pc.route('/api/chat/health', methods=['GET'])
def chat_health():
    """
    检查EmoLLM服务健康状态
    
    Response:
        {
            "status": "healthy/unhealthy",
            "message": "..."
        }
    """
    try:
        emollm_client = get_emollm_client()
        is_healthy = emollm_client.check_health()
        
        if is_healthy:
            return jsonify({
                'status': 'healthy',
                'message': 'EmoLLM服务正常运行'
            })
        else:
            return jsonify({
                'status': 'unhealthy',
                'message': 'EmoLLM服务不可用'
            }), 503
            
    except Exception as e:
        logger.error(f"健康检查异常: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@pc.route('/counseling')
def counseling_page():
    """
    心理咨询页面
    """
    # 检查用户登录状态
    userinfo = session.get('userinfo')
    if not userinfo:
        return redirect('/login')
    
    # 渲染心理咨询页面模板
    return render_template('counseling.html')


@pc.route('/api/counseling/latest-report', methods=['GET'])
def get_latest_report():
    """
    获取用户最新的测评报告数据（用于AI分析）
    
    Response:
        {
            "status": "success",
            "data": {...}  # 报告数据，包括测评报告和SDS答题详情
        }
    """
    try:
        userinfo = session.get('userinfo', {})
        user_id = userinfo.get('id')
        username = userinfo.get('username') or userinfo.get('name')
        
        if not user_id:
            return jsonify({
                'status': 'error',
                'message': '未登录'
            }), 401

        payload = get_latest_assessment_payload(
            user_id=user_id,
            username=username,
            viewer_role=userinfo.get('role'),
        )

        if not payload:
            return jsonify({
                'status': 'success',
                'data': None,
                'message': '暂无测评记录'
            })

        return jsonify({
            'status': 'success',
            'data': payload
        })
    except Exception as e:
        logger.error(f"获取最新报告失败: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@pc.route('/api/counseling/history', methods=['GET'])
def get_counseling_history():
    """
    获取用户的咨询历史记录
    
    Response:
        {
            "status": "success",
            "records": [...]
        }
    """
    try:
        userinfo = session.get('userinfo', {})
        username = userinfo.get('username') or userinfo.get('name')
        
        if not username:
            return jsonify({
                'status': 'error',
                'message': '未登录'
            }), 401
        
        # 从数据库获取历史记录
        records = _get_chat_history(username, limit=50)
        
        return jsonify({
            'status': 'success',
            'records': records
        })
        
    except Exception as e:
        logger.error(f"获取历史记录异常: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ============= 辅助函数 =============


def _parse_optional_int(value):
    if value in (None, "", False):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        logger.warning("忽略非法 report_record_id: %r", value)
        return None


def _build_request_assessment_context(*, user_id, user_role, username, report_record_id=None):
    payload = get_assessment_payload(
        viewer_user_id=user_id,
        viewer_role=user_role,
        username=username,
        report_record_id=report_record_id,
    )
    context = build_assessment_context(payload)
    if context:
        logger.info(
            "已注入评估上下文: user=%s report_record_id=%s has_sds=%s scale_count=%s",
            username,
            report_record_id,
            bool(payload and payload.get('record_id')),
            len((payload or {}).get('latest_scales') or []),
        )
    return context or None


def _try_route_chat_skill(
    *,
    username,
    user_message,
    history,
    include_emotion,
    emotion_context,
    stream,
    web_search,
    request_payload,
):
    """Try to handle the current chat request with a registered skill."""
    if not skill_router or not SkillContext:
        return None

    context = SkillContext(
        username=username,
        message=user_message,
        history=history,
        include_emotion=include_emotion,
        emotion_context=emotion_context,
        stream=stream,
        web_search=web_search,
        request_payload=request_payload,
    )

    result = skill_router.route(context)
    if not result:
        return None

    return {
        'skill_name': result.skill_name,
        'response_text': result.response_text,
        'should_store': result.should_store,
        'emotion_context': result.emotion_context,
        'metadata': result.metadata,
    }


def _iter_stream_chunks(text, chunk_size=24):
    """Split locally generated text into small chunks so the frontend can render progressively."""
    content = str(text or "")
    if not content:
        return
    for idx in range(0, len(content), chunk_size):
        yield content[idx:idx + chunk_size]


def _get_user_emotion_context(username):
    """
    获取用户的情绪上下文数据
    
    Args:
        username: 用户名
        
    Returns:
        dict: 情绪上下文数据
    """
    emotion_context = {}
    
    try:
        # 获取最近的表情识别结果
        sql = """
            SELECT emotion, confidence 
            FROM emotion_records 
            WHERE username = ? 
            ORDER BY timestamp DESC 
            LIMIT 1
        """
        result = db.fetchone(sql, [username])
        if result:
            emotion_context['facial_emotion'] = result[0]
            emotion_context['facial_confidence'] = result[1]
        
        # 获取最近的抑郁评分
        sql = """
            SELECT sds_score 
            FROM test_records 
            WHERE username = ? 
            ORDER BY timestamp DESC 
            LIMIT 1
        """
        result = db.fetchone(sql, [username])
        if result:
            emotion_context['depression_score'] = result[0]
        
        logger.info(f"获取用户 {username} 情绪上下文: {emotion_context}")
        
    except Exception as e:
        logger.error(f"获取情绪上下文失败: {e}")
    
    return emotion_context if emotion_context else None


def _save_chat_record(username, user_message, ai_response, emotion_context):
    """
    保存聊天记录到数据库
    
    Args:
        username: 用户名
        user_message: 用户消息
        ai_response: AI回复
        emotion_context: 情绪上下文
    """
    try:
        import json
        import sqlite3
        
        # 获取数据库连接
        from utils.db import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        
        # 如果表不存在，先创建
        create_table_sql = """
            CREATE TABLE IF NOT EXISTS counseling_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                user_message TEXT NOT NULL,
                ai_response TEXT NOT NULL,
                emotion_context TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        cursor.execute(create_table_sql)
        conn.commit()
        
        # 插入记录
        insert_sql = """
            INSERT INTO counseling_records 
            (username, user_message, ai_response, emotion_context, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """
        cursor.execute(insert_sql, [
            username,
            user_message,
            ai_response,
            json.dumps(emotion_context) if emotion_context else None,
            datetime.datetime.now()
        ])
        conn.commit()
        
        cursor.close()
        conn.close()
        
        logger.info(f"保存聊天记录: 用户={username}")
        
    except Exception as e:
        logger.error(f"保存聊天记录失败: {e}", exc_info=True)


def _get_chat_history(username, limit=50):
    """
    获取聊天历史记录
    
    Args:
        username: 用户名
        limit: 返回记录数
        
    Returns:
        list: 聊天记录列表
    """
    try:
        sql = """
            SELECT user_message, ai_response, timestamp 
            FROM counseling_records 
            WHERE username = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        """
        
        results = db.fetchall(sql, [username, limit])
        
        records = []
        for row in results:
            records.append({
                'user_message': row[0],
                'ai_response': row[1],
                'timestamp': str(row[2])
            })
        
        return records
        
    except Exception as e:
        logger.error(f"获取历史记录失败: {e}")
        return []
