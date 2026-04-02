from flask import Blueprint, session, render_template, request, redirect, jsonify, Response
import datetime
import json
import cv2
import numpy as np
import time

from utils import db
# 使用Dolphin ASR语音识别服务
from utils.speech_recognition_dolphin import dolphin_speech_service as speech_service
print("使用Dolphin ASR语音识别服务")

def get_beijing_time():
    """获取北京时间 - 直接使用系统时间（系统已配置为UTC+8）"""
    # 系统本地时间已经是北京时间，直接返回
    return datetime.datetime.now()


def _normalize_choice_string(choice_value):
    """将数据库中的答案串规范为20位字符串。"""
    normalized = str(choice_value or '').strip()
    digits_only = ''.join(char for char in normalized if char.isdigit())
    return digits_only[:20].ljust(20, '0')


def _choice_string_to_answers(choice_value):
    """将答案串转换为前端可用的答案数组。"""
    normalized = _normalize_choice_string(choice_value)
    return [char if char in {'1', '2', '3', '4'} else None for char in normalized[:20]]


def _answers_payload_to_choice_string(answers_payload):
    """将前端提交的答案对象序列化为20位答案串。"""
    answers_payload = answers_payload or {}
    serialized = []

    for i in range(1, 21):
        answer_data = answers_payload.get(str(i)) or answers_payload.get(i)
        value = None

        if isinstance(answer_data, dict):
            value = answer_data.get('value')
        else:
            value = answer_data

        value_str = str(value).strip() if value is not None else '0'
        serialized.append(value_str if value_str in {'1', '2', '3', '4'} else '0')

    return ''.join(serialized)


def _clamp_progress_index(progress_index):
    try:
        index = int(progress_index)
    except (TypeError, ValueError):
        index = 0

    return max(0, min(19, index))


def _resolve_resume_index(saved_index, answers):
    if saved_index is not None:
        try:
            index = int(saved_index)
        except (TypeError, ValueError):
            index = None
        else:
            if 0 <= index < 20:
                return index

    for idx, answer in enumerate(answers):
        if answer is None:
            return idx

    return 19


def _find_active_test_for_user(user_id):
    return db.fetch_one(
        """
        SELECT id, choose, use_time, progress_index, start_time
        FROM test
        WHERE user_id = ? AND status = '未完成'
        ORDER BY start_time DESC, id DESC
        LIMIT 1
        """,
        [user_id]
    )


def _ensure_active_test_id(user_id, preferred_test_id=None):
    if preferred_test_id:
        existing = db.fetch_one(
            "SELECT id FROM test WHERE id = ? AND user_id = ? AND status = '未完成'",
            [preferred_test_id, user_id]
        )
        if existing:
            return existing['id']

    active_test = _find_active_test_for_user(user_id)
    if active_test:
        return active_test['id']

    now_time = datetime.datetime.now()
    return db.insert(
        "INSERT INTO test (role, user_id, start_time, status, progress_index) VALUES (?, ?, ?, ?, ?)",
        [1, user_id, now_time, "未完成", 0]
    )


def _calculate_sds_result(answers_payload):
    """统一计算 SDS 标准分、等级与完成状态。"""
    answer = _answers_payload_to_choice_string(answers_payload)
    reverse_questions = {2, 5, 6, 11, 12, 14, 16, 17, 18, 20}

    total_raw_score = 0
    for i in range(1, 21):
        key = str(i)
        if key in answers_payload or i in answers_payload:
            answer_data = answers_payload.get(key) or answers_payload.get(i)
            value = answer_data['value'] if isinstance(answer_data, dict) else answer_data
            value = int(value)
            score = 5 - value if i in reverse_questions else value
            total_raw_score += score

    standard_score = int(total_raw_score * 1.25)

    if standard_score < 50:
        result_chinese = "无抑郁"
    elif 50 <= standard_score <= 60:
        result_chinese = "轻度抑郁"
    elif 61 <= standard_score <= 70:
        result_chinese = "中度抑郁"
    else:
        result_chinese = "重度抑郁"

    finish_status = "未完成" if '0' in answer else "已完成"
    return {
        "answer": answer,
        "standard_score": standard_score,
        "result_chinese": result_chinese,
        "finish_status": finish_status,
    }


def _build_sds_comprehensive_payload(*, standard_score, emotion_data=None, eeg_data=None):
    from utils.scoring_system import scoring_system

    emotion_data = emotion_data if isinstance(emotion_data, dict) else {}
    eeg_data = eeg_data if isinstance(eeg_data, dict) else None
    comprehensive_result = scoring_system.calculate_comprehensive_score(
        sds_score=standard_score,
        emotion_data=emotion_data,
        eeg_data=eeg_data,
    )
    return {
        "emotion_json": json.dumps(emotion_data) if emotion_data else None,
        "comprehensive_score": comprehensive_result["comprehensive_score"],
        "comprehensive_json": json.dumps(comprehensive_result),
        "comprehensive_result": comprehensive_result,
    }

# 模块加载完成

try:
    # 导入GPU表情识别服务
    from utils.emotion_recognition_gpu import gpu_emotion_service as npu_emotion_service
    print("使用GPU加速的表情识别服务")
except ImportError as e:
    print(f"表情识别服务不可用: {e}")
    npu_emotion_service = None

# 导入GPU版MJPEG视频流
try:
    from utils import simple_mjpeg_stream_gpu as simple_mjpeg_stream
    print("使用GPU版MJPEG视频流服务")
except ImportError as e:
    print(f"简化版MJPEG视频流服务不可用: {e}")
    simple_mjpeg_stream = None

#蓝图对象
ts = Blueprint("test", __name__)

@ts.route('/SDS/debug', methods=["GET"])
def SDS_debug():
    """调试接口 - 检查session状态"""
    return jsonify({
        'userinfo': session.get("userinfo"),
        'test_id': session.get("test_id"),
        'session_keys': list(session.keys())
    })

@ts.route('/SDS', methods=["GET", "POST"])
def SDS():
    userinfo = session.get("userinfo")
    if not userinfo:
        return redirect('/login')

    flow_session_id = str(request.args.get("flow_session_id") or session.get("sds_flow_session_id") or "").strip()
    if flow_session_id:
        session["sds_flow_session_id"] = flow_session_id

    test_id = _ensure_active_test_id(userinfo['id'], session.get("test_id"))
    active_test = db.fetch_one(
        "SELECT id, choose, use_time, progress_index FROM test WHERE id = ? AND user_id = ?",
        [test_id, userinfo['id']]
    ) or {}

    saved_answers = _choice_string_to_answers(active_test.get('choose'))
    resume_index = _resolve_resume_index(active_test.get('progress_index'), saved_answers)
    session["test_id"] = test_id

    sds_initial_state = {
        'testId': test_id,
        'answers': saved_answers,
        'currentQuestionIndex': resume_index,
        'savedUseTime': int(active_test.get('use_time') or 0),
        'flowSessionId': flow_session_id or None,
    }

    return render_template("SDS_working2.html", sds_initial_state=sds_initial_state)


@ts.route('/SDS/save-progress', methods=["POST"])
def SDS_save_progress():
    userinfo = session.get("userinfo")
    if not userinfo:
        return jsonify({'success': False, 'error': '未登录'}), 401

    data = request.get_json(silent=True) or {}
    answers = data.get('answers') or {}
    total_time = max(0, int(data.get('totalTime') or 0))
    progress_index = _clamp_progress_index(data.get('currentQuestionIndex', 0))

    test_id = _ensure_active_test_id(userinfo['id'], session.get("test_id"))
    session["test_id"] = test_id

    answer_string = _answers_payload_to_choice_string(answers)
    db.update(
        """
        UPDATE test
        SET choose = ?, use_time = ?, progress_index = ?, status = ?
        WHERE id = ? AND user_id = ?
        """,
        [answer_string, total_time, progress_index, "未完成", test_id, userinfo['id']]
    )

    flow_session_id = str(session.get("sds_flow_session_id") or "").strip()
    if flow_session_id:
        try:
            from new_features.scale_assessment.flow_service import save_flow_draft

            save_flow_draft(
                flow_session_id,
                user_id=userinfo['id'],
                scale_slug='sds',
                draft_payload={
                    'test_id': test_id,
                    'progress_index': progress_index,
                    'total_time': total_time,
                    'answered_count': sum(1 for item in answers.values() if item),
                },
            )
        except Exception as exc:
            print(f"SDS 草稿挂接 flow session 失败: {exc}")

    return jsonify({
        'success': True,
        'test_id': test_id,
        'progress_index': progress_index
    })

@ts.route('/SDS/submit', methods=["GET", "POST"])
def SDS_submit():
    userinfo = session.get("userinfo")
    if not userinfo:
        return jsonify({'success': False, 'error': '未登录'}), 401

    test_id = _ensure_active_test_id(userinfo['id'], session.get("test_id"))
    session["test_id"] = test_id

    data = request.get_json(silent=True) or {}
    answers = data.get('answers') or {}
    total_time = max(0, int(data.get('totalTime') or 0))
    finish_time = get_beijing_time()
    progress_index = _clamp_progress_index(data.get('currentQuestionIndex', 19))
    emotion_data = data.get('emotionData') if isinstance(data.get('emotionData'), dict) else {}
    eeg_data = data.get('eegData') if isinstance(data.get('eegData'), dict) else None

    sds_result = _calculate_sds_result(answers)
    answer = sds_result["answer"]
    standard_score = sds_result["standard_score"]
    result_chinese = sds_result["result_chinese"]
    finish_status = sds_result["finish_status"]

    emotion_json = None
    comprehensive_score = None
    comprehensive_json = None
    comprehensive_result = None
    if finish_status == "已完成":
        comprehensive_payload = _build_sds_comprehensive_payload(
            standard_score=standard_score,
            emotion_data=emotion_data,
            eeg_data=eeg_data,
        )
        emotion_json = comprehensive_payload["emotion_json"]
        comprehensive_score = comprehensive_payload["comprehensive_score"]
        comprehensive_json = comprehensive_payload["comprehensive_json"]
        comprehensive_result = comprehensive_payload["comprehensive_result"]

    db.update(
        """
        UPDATE test
        SET finish_time = ?, use_time = ?, progress_index = ?, status = ?,
            result = ?, choose = ?, score = ?, emotion_data = ?,
            comprehensive_score = ?, comprehensive_result = ?
        WHERE id = ?
        """,
        [
            finish_time,
            total_time,
            progress_index,
            finish_status,
            result_chinese,
            answer,
            standard_score,
            emotion_json,
            comprehensive_score,
            comprehensive_json,
            test_id,
        ]
    )

    flow_session_id = str(session.get("sds_flow_session_id") or "").strip()
    if finish_status == "已完成" and flow_session_id:
        try:
            from new_features.scale_assessment.flow_service import attach_sds_completion

            attach_sds_completion(
                flow_session_id,
                user_id=userinfo['id'],
                sds_record_id=test_id,
            )
        except Exception as exc:
            print(f"SDS 完成记录挂接 flow session 失败: {exc}")

    session.pop("test_id", None)

    return jsonify({
        'success': True,
        'message': '提交成功',
        'redirect': f'/submit_success.html?record_id={test_id}',
        'test_id': test_id,
        'record_id': test_id,
        'score': standard_score,
        'result': result_chinese,
        'comprehensive_score': comprehensive_score,
        'comprehensive_result': comprehensive_result,
        'emotion_summary': (emotion_data or {}).get('summary', {}),
        'eeg_summary': eeg_data or {}
    })

@ts.route('/test/process', methods=['POST'])
def process():
    """
    处理SDS量表的语音输入
    支持音频文件上传和语音识别
    """
    try:
        # 检查是否有音频文件
        if 'audio' in request.files:
            # 处理音频文件
            audio_file = request.files['audio']

            if audio_file.filename == '':
                return jsonify({'error': '没有选择音频文件'}), 400

            # 读取音频数据
            audio_data = audio_file.read()

            # 使用语音识别服务进行处理
            result = speech_service.process_speech_for_sds(audio_data)
            
            # 添加额外信息
            result['source'] = 'audio_file'
            result['processed_text'] = result.get('text', '')
            result['auto_selected'] = result.get('answer') is not None

            return jsonify(result)

        elif request.is_json:
            # 处理JSON数据（文本输入）
            data = request.json
            text = data.get('text', '').strip()

            if not text:
                return jsonify({'error': '未接收到语音文本'}), 400

            # 直接从文本中提取答案
            answer = speech_service.extract_answer_from_text(text)

            if answer:
                # 计算置信度（基于文本长度和关键词匹配度）
                confidence = min(0.95, 0.6 + len(text) / 100)  # 基础置信度 + 文本长度加成
                
                response = {
                    'answer': answer,
                    'confidence': confidence,
                    'text': text,
                    'message': f'识别到选项: {answer}',
                    'processed_text': f'语音识别: {text}',
                    'auto_selected': True
                }
            else:
                response = {
                    'answer': None,
                    'confidence': 0.1,
                    'text': text,
                    'message': '无法从语音中识别到有效选项，请尝试更清楚地说出选项',
                    'processed_text': f'语音识别: {text}',
                    'auto_selected': False,
                    'suggestions': [
                        '请尝试说："选择A"、"选B"、"我选C"等',
                        '或直接说数字："1"、"二"、"第三个"等',
                        '或说出对应含义："没有"、"偶尔"、"经常"、"总是"等'
                    ]
                }

            return jsonify(response)
        else:
            return jsonify({'error': '不支持的请求格式'}), 400

    except Exception as e:
        print(f"语音处理错误: {e}")
        return jsonify({'error': f'语音处理失败: {str(e)}'}), 500


@ts.route('/test/speech-status', methods=['GET'])
def get_speech_status():
    """
    获取语音识别服务状态
    """
    try:
        # 检查模型是否已加载
        if speech_service.model is None:
            try:
                speech_service.load_model()
                return jsonify({
                    'status': 'ready',
                    'message': '语音识别服务已启动'
                })
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'message': f'语音识别服务启动失败: {str(e)}'
                })
        else:
            return jsonify({
                'status': 'ready',
                'message': '语音识别服务正在运行'
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'检查服务状态失败: {str(e)}'
        }), 500


@ts.route('/test/speech-test', methods=['POST'])
def test_speech_extraction():
    """
    测试语音文本提取功能
    """
    try:
        data = request.get_json()
        test_text = data.get('text', '').strip()
        
        if not test_text:
            return jsonify({'error': '请提供测试文本'}), 400
        
        # 测试答案提取
        answer = speech_service.extract_answer_from_text(test_text)
        
        return jsonify({
            'input_text': test_text,
            'extracted_answer': answer,
            'success': answer is not None,
            'message': f'从文本"{test_text}"中提取答案: {answer}' if answer else f'无法从文本"{test_text}"中提取有效答案'
        })
        
    except Exception as e:
        return jsonify({
            'error': f'测试失败: {str(e)}'
        }), 500


# ================================================================================
# 表情识别相关API
# ================================================================================

@ts.route('/emotion/detect', methods=['POST'])
def emotion_detect():
    """表情检测API"""
    try:
        if not npu_emotion_service:
            return jsonify({
                'success': False,
                'error': '表情识别服务不可用'
            }), 503
        
        data = request.get_json()
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({
                'success': False,
                'error': '缺少图像数据'
            }), 400
        
        # 进行表情检测
        result = npu_emotion_service.detect_emotion_from_image(image_data)
        
        # 记录详细错误信息
        if not result.get('success', False):
            import traceback
            print(f"表情检测返回失败: {result.get('error', '未知错误')}")
            print(traceback.format_exc())
        
        return jsonify(result)
        
    except Exception as e:
        import traceback
        error_msg = f'表情检测失败: {str(e)}'
        print(f"API异常: {error_msg}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500

@ts.route('/emotion/statistics', methods=['GET'])
def emotion_statistics():
    """获取表情统计数据（优先使用简化版MJPEG服务的统计）"""
    try:
        # 优先使用简化版MJPEG流服务的统计数据
        if simple_mjpeg_stream:
            stats = simple_mjpeg_stream.get_statistics()
            return jsonify({
                'success': True,
                'data': stats,
                'source': 'simple_mjpeg'
            })
        
        # 备用：使用原有服务的统计数据
        if npu_emotion_service:
            stats = npu_emotion_service.get_emotion_statistics()
            return jsonify({
                'success': True,
                'data': stats,
                'source': 'npu_service'
            })
        
        return jsonify({
            'success': False,
            'error': '表情识别服务不可用'
        }), 503
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取统计数据失败: {str(e)}'
        }), 500

@ts.route('/emotion/reset', methods=['POST'])
def emotion_reset():
    """重置表情统计"""
    try:
        reset_count = 0
        
        # 重置简化版MJPEG服务统计
        if simple_mjpeg_stream:
            simple_mjpeg_stream.reset_statistics()
            reset_count += 1
        
        # 重置原有服务统计
        if npu_emotion_service:
            npu_emotion_service.reset_statistics()
            reset_count += 1
        
        if reset_count == 0:
            return jsonify({
                'success': False,
                'error': '表情识别服务不可用'
            }), 503
        
        return jsonify({
            'success': True,
            'message': f'表情统计已重置（{reset_count}个服务）'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'重置统计失败: {str(e)}'
        }), 500

@ts.route('/emotion/service-info', methods=['GET'])
def emotion_service_info():
    """获取表情识别服务信息"""
    try:
        if not npu_emotion_service:
            return jsonify({
                'success': False,
                'error': '表情识别服务不可用'
            }), 503
        
        info = npu_emotion_service.get_service_info()
        return jsonify({
            'success': True,
            'data': info
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取服务信息失败: {str(e)}'
        }), 500

# ================================================================================
# MJPEG视频流 - 简化版，完全模仿 face_emotion.py 的逻辑
# ================================================================================

@ts.route('/emotion/video_stream')
def emotion_video_stream():
    """
    简化版MJPEG视频流端点 - 完全模仿 face_emotion.py
    
    核心逻辑：
    1. 单线程循环，与 face_emotion.py 的 while True 完全对应
    2. 使用 cap.grab() + cap.retrieve() 确保获取最新帧
    3. 不使用 sleep，让循环自然运行（最大化帧率）
    4. 直接调用NPU推理，与 face_emotion.py 一致
    
    前端使用 <img src="/emotion/video_stream"> 即可显示
    """
    if simple_mjpeg_stream is None:
        # 服务不可用，返回错误帧
        error_frame = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.putText(error_frame, "MJPEG Service Unavailable", (10, 120), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        _, buffer = cv2.imencode('.jpg', error_frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        
        def error_generator():
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        
        return Response(
            error_generator(),
            mimetype='multipart/x-mixed-replace; boundary=frame'
        )
    
    return Response(
        simple_mjpeg_stream.generate_mjpeg_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@ts.route('/eeg/latest')
def eeg_latest_data():
    """获取最新的脑电数据（用于实时更新）"""
    try:
        from flask_app.utils.eeg_receiver import get_eeg_receiver
        receiver = get_eeg_receiver()
        latest = receiver.get_latest_data()
        
        return jsonify({
            'success': True,
            'data': latest
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {
                'channel': 0,
                'value': 0.0,
                'theta': 0.0,
                'alpha': 0.0,
                'beta': 0.0,
                'timestamp': time.time()
            }
        })

@ts.route('/eeg/channels')
def eeg_all_channels():
    """获取所有3个通道的数据"""
    try:
        from flask_app.utils.eeg_receiver import get_eeg_receiver
        receiver = get_eeg_receiver()
        all_data = receiver.get_all_channels_data()
        
        return jsonify({
            'success': True,
            'data': all_data
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {
                'channel1': {'waveform': [], 'timestamps': [], 'features': {'current': {}, 'history': {'theta': [], 'alpha': [], 'beta': [], 'timestamps': []}}},
                'channel2': {'waveform': [], 'timestamps': [], 'features': {'current': {}, 'history': {'theta': [], 'alpha': [], 'beta': [], 'timestamps': []}}},
                'channel3': {'waveform': [], 'timestamps': [], 'features': {'current': {}, 'history': {'theta': [], 'alpha': [], 'beta': [], 'timestamps': []}}}
            }
        })

@ts.route('/eeg/classification')
def eeg_classification():
    """规则版情绪分类：积极/中性/消极/待机"""
    try:
        from flask_app.utils.eeg_receiver import get_eeg_receiver
        receiver = get_eeg_receiver()
        result = receiver.get_emotion_classification(window_sec=4.0)
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {}
        })

@ts.route('/eeg/history')
def eeg_history_data():
    """获取历史脑电数据（用于绘制波形图）- 保留兼容性"""
    try:
        from flask_app.utils.eeg_receiver import get_eeg_receiver
        receiver = get_eeg_receiver()
        all_data = receiver.get_all_channels_data()
        
        return jsonify({
            'success': True,
            'data': all_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {}
        })

@ts.route('/eeg-test')
def eeg_test_page():
    """返回脑电数据测试页面"""
    return render_template('eeg_test.html')

@ts.route('/eeg/stream')
def eeg_stream_data():
    """SSE流式传输脑电数据"""
    def generate():
        try:
            from flask_app.utils.eeg_receiver import get_eeg_receiver
            receiver = get_eeg_receiver()
            print("[EEG] SSE流已建立，开始推送数据...")
            
            while True:
                batch = receiver.get_stream_data()
                if batch:
                    try:
                        # 确保数据可以被JSON序列化
                        json_str = json.dumps(batch)
                        yield f"data: {json_str}\n\n"
                        print(f"[EEG] 推送了 {len(batch)} 条数据")
                    except (ValueError, TypeError) as e:
                        print(f"[EEG] JSON序列化失败: {e}")
                        # 发送空数组而不是错误
                        yield f"data: []\n\n"
                else:
                    # 发送心跳包保持连接
                    yield f": heartbeat\n\n"
                
                time.sleep(0.05)  # 20Hz 更新率
                
        except GeneratorExit:
            print("[EEG] SSE流已关闭")
        except Exception as e:
            print(f"[EEG] SSE流错误: {e}")
            yield f"data: {json.dumps([])}\n\n"
    
    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    return response

@ts.route('/emotion/stream_status')
def emotion_stream_status():
    """获取视频流服务状态"""
    if simple_mjpeg_stream is None:
        return jsonify({
            'success': False,
            'error': 'MJPEG服务不可用'
        }), 503
    
    return jsonify({
        'success': True,
        'model_loaded': simple_mjpeg_stream._model_loaded,
        'npu_available': simple_mjpeg_stream.NPU_AVAILABLE
    })

@ts.route('/emotion/stop_stream', methods=['POST'])
def emotion_stop_stream():
    """停止视频流并释放摄像头"""
    if simple_mjpeg_stream is None:
        return jsonify({
            'success': False,
            'error': 'MJPEG服务不可用'
        }), 503
    
    try:
        simple_mjpeg_stream.stop_stream()
        return jsonify({
            'success': True,
            'message': '视频流已停止'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'停止失败: {str(e)}'
        }), 500
