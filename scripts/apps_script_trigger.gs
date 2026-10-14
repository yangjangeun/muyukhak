// Google Apps Script (script.google.com)에 붙여넣어 쓰는 아침 실행 트리거.
// 스크립트 속성 GITHUB_TOKEN 에 GitHub fine-grained 토큰(Actions: Read and write)을 넣는다.
// Apps Script 시간 트리거는 지정 분 ±15분 안에 실행되므로 두 번 걸어 둔다 (하루 1회 전송은 GitHub 쪽 gate가 보장).

const REPO = 'yangjangeun/muyukhak';

function triggerDaily() {
  const token = PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN');
  const res = UrlFetchApp.fetch(
    `https://api.github.com/repos/${REPO}/actions/workflows/daily.yml/dispatches`,
    {
      method: 'post',
      contentType: 'application/json',
      headers: {
        Authorization: 'Bearer ' + token,
        Accept: 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
      },
      payload: JSON.stringify({ ref: 'main' }),
      muteHttpExceptions: true,
    },
  );
  console.log(res.getResponseCode(), res.getContentText());
}

function setup() {
  ScriptApp.getProjectTriggers().forEach((t) => ScriptApp.deleteTrigger(t));
  // 07:15 ±15분 → 07:00~07:30, 07:40 ±15분 → 예비
  [15, 40].forEach((minute) =>
    ScriptApp.newTrigger('triggerDaily')
      .timeBased()
      .atHour(7)
      .nearMinute(minute)
      .everyDays(1)
      .inTimezone('Asia/Seoul')
      .create(),
  );
  console.log('트리거 등록 완료');
}
