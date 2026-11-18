import argparse
import json
import os
import queue
import re
import threading
import time
from contextlib import contextmanager
from datetime import datetime

import numpy as np
from flask import Flask, Response, jsonify, request
from PIL import Image

from internnav.agent.internvla_n1_agent_realworld import InternVLAN1AsyncAgent

app = Flask(__name__)
idx = 0
start_time = time.time()
output_dir = ''


@contextmanager
def pixel_notifications(model_agent, callback):
    """Notify on decoded coordinates before latent/trajectory generation finishes."""
    if callback is None:
        yield
        return
    tokenizer = model_agent.processor.tokenizer
    original_decode = tokenizer.decode

    def decode(*pos, **kw):
        text = original_decode(*pos, **kw)
        # Match the agent's coordinate extraction without changing its output.
        coords = re.findall(r'\d+', text)
        if len(coords) >= 2:
            callback([int(coords[1]), int(coords[0])])
        return text

    tokenizer.decode = decode
    try:
        yield
    finally:
        tokenizer.decode = original_decode


def inference_stream(infer, correlation):
    """Deliver pixel notification and final result over the same HTTP response."""
    outgoing = queue.Queue()

    def pixel_ready(pixel):
        outgoing.put(dict(event='pixel_goal', **correlation, pixel_goal=pixel))

    def work():
        try:
            result = infer(pixel_ready)
            outgoing.put(dict(event='result', **correlation, response=result))
        except Exception as exc:
            outgoing.put(dict(event='error', **correlation, message=str(exc)))

    threading.Thread(target=work, daemon=True).start()

    def chunks():
        yield json.dumps(dict(event='started', **correlation)) + '\n'
        while True:
            event = outgoing.get()
            yield json.dumps(event) + '\n'
            if event['event'] in ('result', 'error'):
                break

    return Response(chunks(), mimetype='application/x-ndjson', headers={
        'X-InternNav-Pixel-Stop': '1', 'X-Accel-Buffering': 'no', 'Cache-Control': 'no-cache'})


def resolve_instruction(default_instruction):
    # An explicitly empty environment variable is an error, not permission to
    # silently fall back to a different navigation task.
    instruction = os.environ.get("NAV_INSTRUCTION", default_instruction)
    if not isinstance(instruction, str) or not instruction.strip():
        raise ValueError(
            "Navigation instruction is empty. Set a non-empty NAV_INSTRUCTION, "
            "or unset NAV_INSTRUCTION and supply --instruction."
        )
    return instruction


@app.route("/eval_dual", methods=['POST'])
def eval_dual():
    global idx, output_dir, start_time
    # Validate every request, before decoding images, resetting the episode,
    # creating output directories/files, or invoking either inference pass.
    try:
        instruction = resolve_instruction(args.instruction)
    except ValueError as exc:
        app.logger.warning("Rejected /eval_dual: %s", exc)
        return jsonify(error="empty_instruction", message=str(exc)), 400

    start_time = time.time()

    image_file = request.files['image']
    depth_file = request.files['depth']
    json_data = request.form['json']
    data = json.loads(json_data)
    # Keep the existing wire field for compatibility; no diagnostic recording.
    context = data.get('diagnostic', {})
    if not isinstance(context, dict):
        context = {}

    image = Image.open(image_file.stream)
    image = image.convert('RGB')
    image = np.asarray(image)

    depth = Image.open(depth_file.stream)
    depth = depth.convert('I')
    depth = np.asarray(depth)
    depth = depth.astype(np.float32) / 10000.0
    print(f"read http data cost {time.time() - start_time}")

    def infer(on_pixel=None):
        global idx, output_dir, start_time
        camera_pose = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])
        policy_init = data['reset']
        if policy_init:
            start_time = time.time()
            idx = 0
            output_dir = 'output/runs' + datetime.now().strftime('%m-%d-%H%M')
            os.makedirs(output_dir, exist_ok=True)
            print("init reset model!!!")
            agent.reset()
            # Keep the actual instruction alongside this run's images and LLM outputs.
            with open(os.path.join(agent.save_dir, "instruction.txt"), "w", encoding="utf-8") as f:
                f.write(instruction)

        idx += 1
        look_down = False
        t0 = time.time()
        with pixel_notifications(agent, on_pixel):
            dual_sys_output = agent.step(
                image, depth, camera_pose, instruction, intrinsic=args.camera_intrinsic, look_down=look_down
            )
            if dual_sys_output.output_action is not None and dual_sys_output.output_action == [5]:
                look_down = True
                dual_sys_output = agent.step(
                    image, depth, camera_pose, instruction, intrinsic=args.camera_intrinsic, look_down=look_down
                )

        json_output = {}
        if dual_sys_output.output_action is not None:
            json_output['discrete_action'] = dual_sys_output.output_action
        else:
            json_output['trajectory'] = dual_sys_output.output_trajectory.tolist()
            if dual_sys_output.output_pixel is not None:
                json_output['pixel_goal'] = dual_sys_output.output_pixel

        generate_time = time.time() - t0
        print(f"dual sys step {generate_time}")
        print(f"json_output {json_output}")
        return json_output

    if context.get('pixel_stop_protocol') == 1:
        correlation = dict(request_id=context.get('request_id'),
                           client_run_id=context.get('client_run_id'))
        return inference_stream(infer, correlation)
    return jsonify(infer())


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("--device", type=str, default="cuda:0")
    parser.add_argument("--model_path", type=str, default="checkpoints/InternVLA-N1")
    parser.add_argument("--resize_w", type=int, default=384)
    parser.add_argument("--resize_h", type=int, default=384)
    parser.add_argument("--num_history", type=int, default=8)
    parser.add_argument("--plan_step_gap", type=int, default=4)
    parser.add_argument("--instruction", type=str, default="Go forward and stop at the target.")
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5801)
    parser.add_argument("--camera_fx", type=float, default=388.5428466796875)
    parser.add_argument("--camera_fy", type=float, default=387.49945068359375)
    parser.add_argument("--camera_cx", type=float, default=325.6728515625)
    parser.add_argument("--camera_cy", type=float, default=244.2130889892578)
    args = parser.parse_args()

    # Fail before model initialization and warm-up if startup configuration is empty.
    try:
        resolve_instruction(args.instruction)
    except ValueError as exc:
        parser.error(str(exc))

    args.camera_intrinsic = np.array(
        [[args.camera_fx, 0.0, args.camera_cx, 0.0], [0.0, args.camera_fy, args.camera_cy, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]
    )
    agent = InternVLAN1AsyncAgent(args)
    agent.reset(save_output=False)
    agent.step(
        np.zeros((480, 640, 3), dtype=np.uint8),
        np.zeros((480, 640), dtype=np.float32),
        np.eye(4),
        "hello",
        args.camera_intrinsic,
    )
    agent.reset(save_output=False)

    app.run(host=args.host, port=args.port)
