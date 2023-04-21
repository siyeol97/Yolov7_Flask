import pandas as pd


class Chatbot():
    def __init__(self):
        self.chatbot_data = pd.read_excel(
            "./chatbot_data.xlsx")
        self.chat_dic = {}
        i = 0
        for rule in self.chatbot_data["rule"]:
            self.chat_dic[i] = rule.split("|")
            i += 1

    def chat_rule(self, request):
        for key, val in self.chat_dic.items():
            # rule에 포함되어 있는지를 확인하기 위한 변수 지정( False로 초기화)
            chat_flag = False

            # value값은 리스트형이므로
            for word in val:
                if word in request:
                    chat_flag = True
                else:
                    chat_flag = False
                    break  # rule에 일치하는 단어가 하나라도 있다면 더 검사x 바로 종료

            # 질문에 rule이 있을 때
            if chat_flag:
                return self.chatbot_data["response"][key]

        # 질문에 대한 rule이 없다면
        return "죄송합니다. 답변할 수 없는 질문입니다. \n현재 불량률, 실시간 화면, 불량 상황과 같은 질문을 해주십시오."

    def chatting(self):
        while True:
            # 외부장치 오류 있을 수 있으므로 try, except로
            try:
                req = input("나 : ")

                if req == "exit":
                    break

                # 질문을 함수에 보내서 응답메세지 받아오기
                else:
                    print("ChatBot : ", self.chat_rule(req))
            except:
                print("알 수 없는 오류가 발생했습니다. 종료합니다.")
                break
