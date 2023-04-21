function sendReq() {
    var req = document.getElementById("req").value;
    var chat = document.getElementById("chat");
    var xhr = new XMLHttpRequest();
    xhr.onreadystatechange = function() {
      if (xhr.readyState == 4 && xhr.status == 200) {
        var res = xhr.responseText;	

        var user_input = document.createElement("p");
        user_input.innerText = "User : " + req;
        user_input.classList.add("user");

        // avatar 삽입
        var user_avatar = document.createElement("div");
        user_avatar.classList.add("user");
        user_avatar.classList.add("avatar");
        
        var chatbot_avatar = document.createElement("div");
        chatbot_avatar.classList.add("chatbot");
        chatbot_avatar.classList.add("avatar");             

        chat.appendChild(user_avatar);
        chat.appendChild(user_input);

        var chatbot_output = document.createElement("p");
        if (res === '실시간 상황입니다.') {
          var a = document.createElement('a');
          var linkText = document.createTextNode("실시간 웹캠 보기");
          a.appendChild(linkText);
          a.title = "웹캠 보기";
          a.href = "/webcam_feed";
          a.target = "_blank";
          chatbot_output.appendChild(a);
          chatbot_output.classList.add("chatbot");
          chat.appendChild(chatbot_avatar);
          chat.appendChild(chatbot_output);
          chat.scrollTop = chat.scrollHeight; //자동스크롤
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
                    chat.appendChild(chatbot_avatar);
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
                    chat.appendChild(chatbot_output_detected);
                    chat.scrollTop = chat.scrollHeight; //자동스크롤
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
        
        else if (res === '기계이상') {
          // Send a new XHR request to /load_data and display the response as a message
          var xhr3 = new XMLHttpRequest();
          xhr3.onreadystatechange = function() {
            if (xhr3.readyState === 4 && xhr3.status === 200) {
              var message = "기계이상 상태는 " + (xhr3.responseText) + "입니다.";
              chatbot_output.innerText = message;
              chatbot_output.classList.add("chatbot");
              chat.appendChild(chatbot_avatar);
              chat.appendChild(chatbot_output);
              chat.scrollTop = chat.scrollHeight; //자동스크롤
            }
          };
          xhr3.open("GET", "/machpred", true);
          xhr3.send();
        }
        
        else {
          chatbot_output.innerText = res;
          chatbot_output.classList.add("chatbot");
          chat.appendChild(chatbot_avatar);
          chat.appendChild(chatbot_output);
          chat.scrollTop = chat.scrollHeight; //자동스크롤
      }
    }
  };
    xhr.open("POST", "/chat", true);
    xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
    xhr.send("req=" + req);
    document.getElementById("req").value = "";
    return false;
  }