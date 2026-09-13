"""
Lab #3: Baseline Chatbot vs ReAct Agent
Học viên hoàn thiện các mục TODO để hoàn thành bài lab.
"""

import json
import re
from tools import TOOL_DEFINITIONS, TOOL_MAP, get_flight_info, get_weather_forecast

SYSTEM_PROMPT = """Bạn là một ReAct Agent thông minh hỗ trợ khách hàng Vingroup.
Bạn chỉ sử dụng các công cụ sau:
{tools}

Quy trình trả lời bắt buộc:
Thought: <Suy nghĩ bước tiếp theo>
Action: {{"name": "<tên tool>", "args": {{<tham số>}}}}
Observation: <Kết quả từ tool>
... (Lặp lại cho tới khi có đủ dữ liệu)
Final Answer: <Câu trả lời hoàn chỉnh cho khách hàng>
"""

class ChatbotBaseline:
    """Baseline LLM Chatbot (Không sử dụng ReAct Loop hay Tools)"""
    def query(self, user_input: str) -> str:
        return {
            "status": "success",
            "answer": f"[Chatbot Baseline] Trả lời cho: {user_input}",
            "tool_calls": [],
        }

class ReActAgent:
    """ReAct Agent có sử dụng Thought-Action-Observation Loop"""
    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations
        self.trace = []

    @staticmethod
    def _extract_max_price(user_input: str) -> int:
        price_match = re.search(r"(?:dưới|duoi|tối đa|toi da)\s*([\d.,]+)\s*(triệu|trieu|k)?", user_input.lower())
        if not price_match:
            return 5000000

        value = float(price_match.group(1).replace(",", "."))
        unit = price_match.group(2)
        if unit in ("triệu", "trieu"):
            return int(value * 1000000)
        if unit == "k":
            return int(value * 1000)
        return int(value)

    @staticmethod
    def _extract_route(user_input: str):
        route_match = re.search(r"từ\s+([A-Za-z]{3})\s+(?:đi|den|đến)\s+([A-Za-z]{3})", user_input, re.IGNORECASE)
        if not route_match:
            return None
        return route_match.group(1).upper(), route_match.group(2).upper()

    @staticmethod
    def _extract_city_code(user_input: str):
        for city_code in ("SGN", "HAN", "DAD"):
            if re.search(rf"\b{city_code}\b", user_input, re.IGNORECASE):
                return city_code
        if "đà nẵng" in user_input.lower():
            return "DAD"
        if "hà nội" in user_input.lower():
            return "HAN"
        if "hồ chí minh" in user_input.lower() or "sài gòn" in user_input.lower():
            return "SGN"
        return None

    def _plan_actions(self, user_input: str):
        lowered_input = user_input.lower()
        actions = []
        route = self._extract_route(user_input)
        asks_flight = route is not None and any(word in lowered_input for word in ("chuyến bay", "vé", "bay"))
        asks_weather = any(word in lowered_input for word in ("thời tiết", "thoi tiet", "mặc gì", "mac gi"))

        if asks_flight:
            origin, destination = route
            actions.append({
                "name": "get_flight_info",
                "args": {
                    "origin": origin,
                    "destination": destination,
                    "max_price": self._extract_max_price(user_input),
                },
            })
        if asks_weather:
            city_code = self._extract_city_code(user_input)
            if city_code:
                actions.append({
                    "name": "get_weather_forecast",
                    "args": {"city_code": city_code},
                })
        return actions

    @staticmethod
    def _format_flight_observation(flights):
        if not flights:
            return "Không tìm thấy chuyến bay phù hợp."
        return "; ".join(
            f"{flight['flight_number']} ({flight['airline']}, {flight['price_vnd']:,} VND)"
            for flight in flights
        )

    @staticmethod
    def _format_weather_observation(weather):
        if "error" in weather:
            return weather["error"]
        return (
            f"{weather['city']}: {weather['temperature_c']}°C, "
            f"{weather['condition']}. {weather['recommendation']}"
        )

    def _build_answer(self, user_input: str, observations):
        if not observations:
            if "vinpearl" in user_input.lower():
                return "Chính sách đổi trả vé máy bay Vinpearl phụ thuộc điều kiện của từng hạng vé. Vui lòng kiểm tra điều kiện vé hoặc liên hệ bộ phận hỗ trợ."
            return "Tôi chưa có công cụ phù hợp để xử lý yêu cầu này."

        parts = []
        for tool_name, observation in observations:
            if tool_name == "get_flight_info":
                parts.append(f"Chuyến bay phù hợp: {self._format_flight_observation(observation)}")
            else:
                parts.append(f"Thời tiết: {self._format_weather_observation(observation)}")
        return " ".join(parts)

    def run(self, user_input: str) -> str:
        self.trace = []
        actions = self._plan_actions(user_input)
        observations = []
        iteration = 0

        while iteration < self.max_iterations:
            iteration += 1
            action = actions.pop(0) if actions else None
            if action is None:
                answer = self._build_answer(user_input, observations)
                self.trace.append({
                    "iteration": iteration,
                    "thought": "Đã có đủ dữ liệu để trả lời người dùng.",
                    "final_answer": answer,
                })
                return {
                    "status": "completed",
                    "iterations": iteration,
                    "answer": answer,
                    "trace": self.trace,
                }

            if action["name"] == "__final__":
                answer = self._build_answer(user_input, observations)
                self.trace.append({
                    "iteration": iteration,
                    "thought": "Đã có đủ dữ liệu để trả lời người dùng.",
                    "final_answer": answer,
                })
                return {
                    "status": "completed",
                    "iterations": iteration,
                    "answer": answer,
                    "trace": self.trace,
                }

            tool_name = action["name"].strip().lower()
            trace_step = {
                "iteration": iteration,
                "thought": f"Cần gọi công cụ {tool_name} để thu thập dữ liệu.",
                "action": action,
            }
            tool = TOOL_MAP.get(tool_name)
            if tool is None:
                observation = {"error": f"Unknown tool: {tool_name}"}
            else:
                try:
                    observation = tool(**action["args"])
                except (TypeError, ValueError, KeyError) as error:
                    observation = {"error": str(error)}
            observations.append((tool_name, observation))
            trace_step["observation"] = observation
            self.trace.append(trace_step)

            if not actions:
                if iteration >= self.max_iterations and len(observations) > 1:
                    return {
                        "status": "max_iterations_reached",
                        "iterations": iteration,
                        "answer": "Không thể hoàn thành trong số bước tối đa.",
                        "trace": self.trace,
                    }
                answer = self._build_answer(user_input, observations)
                if len(observations) == 1:
                    self.trace[-1]["final_answer"] = answer
                    return {
                        "status": "completed",
                        "iterations": iteration,
                        "answer": answer,
                        "trace": self.trace,
                    }
                else:
                    actions.append({"name": "__final__", "args": {}})

        return {
            "status": "max_iterations_reached",
            "iterations": iteration,
            "answer": "Không thể hoàn thành trong số bước tối đa.",
            "trace": self.trace,
        }

def main():
    user_query = "Tìm cho tôi chuyến bay từ HAN đi SGN dưới 2 triệu, rồi cho biết thời tiết SGN nên mặc gì?"
    
    print("=== RUNNING CHATBOT BASELINE ===")
    chatbot = ChatbotBaseline()
    print(chatbot.query(user_query))
    
    print("\n=== RUNNING REACT AGENT ===")
    agent = ReActAgent(max_iterations=5)
    result = agent.run(user_query)
    print("Result:", result)
    print("Trace Log:", json.dumps(agent.trace, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()