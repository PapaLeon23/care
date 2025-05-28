// static/js/main.js
document.addEventListener('DOMContentLoaded', function() {
    // 플래시 메시지 자동 숨김 처리
    const flashMessagesContainer = document.querySelector('.flash-messages-container');
    if (flashMessagesContainer) {
        const flashMessages = Array.from(flashMessagesContainer.querySelectorAll('.alert'));
        flashMessages.forEach(function(message, index) {
            setTimeout(function() {
                message.classList.add('fade-out');
                message.addEventListener('transitionend', function() {
                    message.remove();
                    if (flashMessagesContainer.children.length === 0) {
                        // flashMessagesContainer.style.display = 'none'; // 필요시 컨테이너도 숨김
                    }
                });
            }, 3000 + (200 * index));
        });
    }
})
//     const togglePayDetailsButton = document.getElementById('togglePayDetailsButton');
//     if (togglePayDetailsButton) {
//         togglePayDetailsButton.addEventListener('click', function() {
//             const dataContainer = document.getElementById('pay-details-data-container');
//             if (dataContainer) {
//                 try {
//                     const workDetailsRawString = dataContainer.dataset.workDetails;
//                     let workDetailsRaw = []; // 기본값을 빈 배열로 설정

//                     // 데이터 문자열이 실제로 존재하고, 비어있지 않은 경우에만 파싱 시도
//                     if (workDetailsRawString && workDetailsRawString.trim() !== "") {
//                         try {
//                             const parsedData = JSON.parse(workDetailsRawString);
//                             // 파싱된 데이터가 배열인지 확인
//                             if (Array.isArray(parsedData)) {
//                                 workDetailsRaw = parsedData;
//                             } else {
//                                 // 유효한 JSON이지만 배열이 아닌 경우 (예: "null" 문자열이 파싱된 경우)
//                                 // workDetailsRaw는 이미 빈 배열로 초기화되어 있으므로 추가 처리 불필요하거나 경고 로깅
//                                 if (parsedData !== null) {
//                                     console.warn("파싱된 근무 상세 정보가 배열 형태가 아닙니다:", parsedData);
//                                 }
//                             }
//                         } catch (parseError) {
//                             // JSON 파싱 중 오류 발생 시, 해당 오류와 원본 데이터 문자열을 콘솔에 기록
//                             console.error("workDetails JSON 파싱 실패:", parseError);
//                             console.error("파싱 오류 시 원본 데이터 문자열:", workDetailsRawString);
//                             // 여기서 오류를 다시 던져 외부 catch 블록에서 처리하도록 함
//                             throw parseError; 
//                         }
//                     }
                    
//                     const yearString = dataContainer.dataset.year;
//                     const monthString = dataContainer.dataset.month;
//                     const year = parseInt(yearString);
//                     const month = parseInt(monthString);

//                     // year 또는 month가 유효한 숫자가 아닌 경우 오류 처리
//                     if (isNaN(year) || isNaN(month)) {
//                         console.error("연도 또는 월 정보가 숫자가 아닙니다. 연도:", yearString, "월:", monthString);
//                         alert("날짜 정보가 올바르지 않아 상세 정보를 표시할 수 없습니다.");
//                         return; // 함수 종료
//                     }
                    
//                     openPayDetailsWindow(workDetailsRaw, year, month);

//                 } catch (e) { // 여기가 기존의 "상세 정보를 불러오는 중 오류가 발생했습니다." 알림 부분
//                     console.error("급여 상세 정보 처리 또는 팝업 호출 중 오류 발생:", e);
//                     // workDetailsRawString이 이미 위에서 콘솔에 찍혔을 수 있으므로, 여기서는 e (오류 객체)를 더 자세히 보는 것이 좋음
//                     if (e instanceof SyntaxError) { // JSON.parse 오류인 경우
//                          alert("근무 상세 정보(JSON)를 파싱하는 중 오류가 발생했습니다. 콘솔을 확인해주세요.");
//                     } else {
//                          alert("상세 정보를 불러오는 중 오류가 발생했습니다.");
//                     }
//                 }
//             } else {
//                 console.warn("#pay-details-data-container 요소를 찾을 수 없습니다.");
//                 alert("상세 정보 컨테이너를 찾을 수 없어 정보를 표시할 수 없습니다.");
//             }
//         });
//     }
//     // ... (openPayDetailsWindow 함수는 기존 코드 유지) ...
// }); // DOMContentLoaded의 닫는 괄호

// // 급여 상세 보기 팝업 함수 (전역 스코프) - 기존 코드 유지
// function openPayDetailsWindow(workDetailsForPayRaw, selectedYear, selectedMonth) {
//     const detailsWindow = window.open('', 'PayDetailsWindow', 'width=700,height=600,scrollbars=yes,resizable=yes');
//     if (!detailsWindow) {
//         alert("팝업 창이 차단되었을 수 있습니다. 팝업 차단을 해제해주세요.");
//         return;
//     }

//     // HTML 내용을 문자열로 구성 (기존 코드 유지)
//     let newWindowContent = `<!DOCTYPE html>
// <html lang="ko">
// <head>
//     <meta charset="UTF-8">
//     <title>${selectedYear}년 ${selectedMonth}월 급여 산정 상세 내역</title>
//     <style>
//         body { font-family: 'Noto Sans KR', sans-serif; padding: 20px; font-size: 14px; line-height: 1.6; color: #333; }
//         .header-title { font-size: 1.6em; color: #0056b3; border-bottom: 2px solid #007BFF; padding-bottom: 10px; margin-bottom: 20px; text-align: center;}
//         table { width: 100%; border-collapse: collapse; margin-top: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
//         th, td { border: 1px solid #ddd; padding: 10px 12px; text-align: left; }
//         th { background-color: #f0f8ff; font-weight: 500; color: #0056b3; }
//         tr:nth-child(even) { background-color: #f9f9f9; }
//         tr:hover { background-color: #f1f1f1; }
//         td.number-cell { text-align: right; }
//         .total-summary { margin-top: 25px; padding-top:15px; border-top: 2px solid #007BFF;}
//         .total-summary p { font-size: 1.15em; margin-bottom: 8px;}
//         .total-summary strong { font-weight: bold; color: #007BFF; } /* CSS 변수 대신 직접 색상 지정 */
//     </style>
// </head>
// <body>
//     <h1 class="header-title">${selectedYear}년 ${selectedMonth}월 급여 산정 상세 내역</h1>`;

//     if (workDetailsForPayRaw && Array.isArray(workDetailsForPayRaw) && workDetailsForPayRaw.length > 0) { // Array.isArray 추가
//         newWindowContent += `
//             <table>
//                 <thead>
//                     <tr>
//                         <th>날짜 (요일)</th>
//                         <th>근무 형태 및 시간</th>
//                         <th class="number-cell">산정 시간</th>
//                         <th class="number-cell">산정 급여</th>
//                     </tr>
//                 </thead>
//                 <tbody>`; 
//         let totalHours = 0;
//         let totalPay = 0;
//         workDetailsForPayRaw.forEach(function(detail) {
//             newWindowContent += `
//                     <tr>
//                         <td>${detail.date || ''}</td>
//                         <td>${detail.shift || ''}</td>
//                         <td class="number-cell">${detail.hours || '0'}</td>
//                         <td class="number-cell">${detail.pay || '0'}</td>
//                     </tr>`; 
//             totalHours += parseFloat(detail.hours_val || 0);
//             totalPay += parseInt(detail.pay_val || 0);
//         });
//         newWindowContent += `
//                 </tbody>
//             </table>
//             <div class="total-summary">
//                 <p><strong>총 근무 시간:</strong> ${totalHours.toFixed(1)}시간</p>
//                 <p><strong>총 급여:</strong> ${totalPay.toLocaleString()}원</p>
//             </div>`;
//     } else {
//         newWindowContent += "<p>해당 월의 근무 기록이 없습니다.</p>";
//     }

//     newWindowContent += `
// </body>
// </html>`; 

//     detailsWindow.document.open();
//     detailsWindow.document.write(newWindowContent);
//     detailsWindow.document.close();
//     detailsWindow.focus();