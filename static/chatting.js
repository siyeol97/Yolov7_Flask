function sendReq() {
    var req = document.getElementById("req").value;
    var chat = document.getElementById("chat");
    var xhr = new XMLHttpRequest(); //app.py의 chat()함수에서 반환된 res 받아오려고..

    xhr.onreadystatechange = function() {
        if (xhr.readyState == 4 && xhr.status == 200) {
            var res = xhr.responseText; //app.py의 chat()함수에서 반환된 res 받아오려고..

            var user_input = document.createElement("p");
            user_input.innerText = req;
            user_input.classList.add("user");
            chat.appendChild(user_input);
            //var chatbot_output = document.createElement("p");
            
            if(res == '실시간 상황입니다.'){
                console.log("실시간 상황입니다 부분")
                var chatbot_output = document.createElement("p");
                var chatbot_output_link = document.createElement("a"); // 하이퍼링크 생성
                chatbot_output_link.href = "/webcam_feed"; // href 속성 지정
                chatbot_output_link.target = "_blank"; // 새 창에서 열기
                chatbot_output_link.innerText = "\n->실시간 상황 보러가기"; // 링크 텍스트 지정
                chatbot_output.appendChild(document.createTextNode(res)); // 문자열 추가
                chatbot_output.appendChild(chatbot_output_link); // 링크 추가
                chatbot_output.classList.add("chatbot");
                chat.appendChild(chatbot_output);
            }
            
            else if(res == '불량률'){
                console.log('불량률 알림 실행')
                var xhr2 = new XMLHttpRequest(); // /get_data 엔드포인트로 요청을 보내기 위한 XMLHttpRequest 객체 생성
                var chatbot_output_detected = document.createElement("p");
                var chatbot_output2 = document.createElement("p");
                const now = new Date();
                const currentTimeString = now.toLocaleString('ko-KR', {timeZone: 'Asia/Seoul'});
                console.log(currentTimeString);

                xhr2.onreadystatechange = function() {
                    if (xhr2.readyState == 4 && xhr2.status == 200) {
                        // /get_data 엔드포인트에서 반환된 JSON 데이터 파싱
                        var data = JSON.parse(xhr2.responseText); // data는 JSON 객체 
                        chatbot_output2.innerText = "현재 시각 : " + currentTimeString + "\n기준 불량률 입니다." + "\n"; // 응답 메시지 출력
                        chatbot_output2.classList.add("chatbot");
                        chat.appendChild(chatbot_output2);
                        const detect = {'name' : [], 'confidence' : [], 'time' : []};
                        
                        for (var i = 0; i < data.length; i++) {
                            var item = data[i];
                            var name = item.name;
                            var confidence = item.confidence;
                            var time = item.time;
                            detect.name.push(name)
                            detect.confidence.push(confidence)
                            detect.time.push(time)
                        }

                        chatbot_output_detected.classList.add("chatbot");
                        var chatbot_output_goResult = document.createElement("a");
                        chatbot_output_goResult.href = "/detectResult"
                        chatbot_output_goResult.target = "_blank";
                        chatbot_output_goResult.innerText = "탐지 결과 보러 가기"
                        chatbot_output_detected.appendChild(chatbot_output_goResult);
                        chat.scrollTop = chat.scrollHeight; //자동스크롤
                        chat.appendChild(chatbot_output_detected);
                        console.log(detect);

                        // detect 딕셔너리를 서버로 전송
                        var xhr3 = new XMLHttpRequest();
                        xhr3.open("POST", "/detectResult", true);
                        xhr3.setRequestHeader("Content-Type", "application/json");
                        xhr3.send(JSON.stringify(detect));
                    }

                }
                xhr2.open("GET", "/get_data", true); // /get_data 엔드포인트로 GET 요청 전송
                xhr2.send();
            }  

            else {
                var chatbot_output = document.createElement("p");
                console.log("else 부분 실행")
                chatbot_output.innerText = res;
                chatbot_output.classList.add("chatbot");
                chat.appendChild(chatbot_output);
                chat.scrollTop = chat.scrollHeight; //자동스크롤
            }
        } 
    };
    xhr.open("POST", "/chat", true);
    xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
    xhr.send("req=" + req);
    document.getElementById("req").value = "";
    return false; // 없으면 폼 제출하고 새로고침됨
};