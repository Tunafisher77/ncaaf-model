var NCAAF_BEST_CARD_TAB = 'NCAAF Best Card Email Summary';
var NCAAF_BEST_CARD_SENT_WEEK = 'NCAAF_BEST_CARD_SENT_WEEK';

function sendNcaafBestCardNow() {
  sendNcaafBestCard_(true);
}

function runNcaafBestCardFridayCheck() {
  sendNcaafBestCard_(false);
}

function sendNcaafBestCard_(forceSend) {
  var zone = 'America/Los_Angeles';
  if (!forceSend && Utilities.formatDate(new Date(), zone, 'u') !== '5') return;

  var lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) {
    if (forceSend) throw new Error('Another NCAAF email run is already active. Wait one minute and try again.');
    return;
  }

  try {
    var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = spreadsheet.getSheetByName(NCAAF_BEST_CARD_TAB);
    if (!sheet || sheet.getLastRow() < 2) {
      if (forceSend) throw new Error('The NCAAF Best Card Email Summary tab is missing or empty.');
      return;
    }

    var values = sheet.getDataRange().getDisplayValues();
    var season = findNcaafValue_(values, 'Season');
    var week = findNcaafValue_(values, 'Week');
    if (!season || !week) {
      if (forceSend) throw new Error('Season or Week is missing from the NCAAF summary tab.');
      return;
    }

    var key = season + '-W' + week;
    var props = PropertiesService.getScriptProperties();
    if (!forceSend && props.getProperty(NCAAF_BEST_CARD_SENT_WEEK) === key) return;

    var recipient = Session.getEffectiveUser().getEmail() || Session.getActiveUser().getEmail();
    if (!recipient) throw new Error('Google did not provide an email recipient for this account.');

    var html = '<div style="font-family:Arial,sans-serif;font-size:14px;color:#111">';
    values.forEach(function(row) {
      var a = row[0] || '';
      var b = row[1] || '';
      if (!a && !b) {
        html += '<br>';
        return;
      }
      if (a === 'Weekly NCAAF Top 25 Best Card' || a === "LAST WEEK'S RESULTS" || a === "THIS WEEK'S BEST CARD") {
        html += '<h2 style="margin-top:24px">' + escapeNcaaf_(a) + '</h2>';
        return;
      }
      if (a.indexOf('GAME ') === 0) {
        html += '<h3 style="margin-top:20px">' + escapeNcaaf_(a) + '</h3><p>' + escapeNcaaf_(b) + '</p>';
        return;
      }
      var color = b.indexOf(' — HIT') >= 0 ? '#16794b' : (b.indexOf(' — MISS') >= 0 ? '#b42318' : '#111');
      html += '<p style="color:' + color + '"><strong>' + escapeNcaaf_(a) + ':</strong> ' + escapeNcaaf_(b) + '</p>';
    });
    html += '<p style="font-size:12px;color:#666;margin-top:24px">Spread is frozen from the Friday-morning odds feed. Player selections are statistics-based and roster-verified.</p></div>';

    MailApp.sendEmail({
      to: recipient,
      subject: 'Weekly NCAAF Top 25 Best Card — ' + season + ' Week ' + week,
      htmlBody: html,
      body: values.map(function(r) { return r.filter(String).join(': '); }).join('\n'),
      name: 'Weekly NCAAF Best Card'
    });

    props.setProperty(NCAAF_BEST_CARD_SENT_WEEK, key);
    console.log('NCAAF Best Card email sent to ' + recipient + ' for ' + key);
  } finally {
    lock.releaseLock();
  }
}

function findNcaafValue_(values, label) {
  for (var i = 0; i < values.length; i++) {
    if (values[i][0] === label) return values[i][1];
  }
  return '';
}

function escapeNcaaf_(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function installNcaafBestCardFridayTriggers() {
  ScriptApp.getProjectTriggers().forEach(function(t) {
    if (t.getHandlerFunction() === 'runNcaafBestCardFridayCheck') ScriptApp.deleteTrigger(t);
  });

  [6, 7, 8, 9, 10, 11, 12].forEach(function(hour) {
    ScriptApp.newTrigger('runNcaafBestCardFridayCheck')
      .timeBased()
      .onWeekDay(ScriptApp.WeekDay.FRIDAY)
      .atHour(hour)
      .nearMinute(5)
      .inTimezone('America/Los_Angeles')
      .create();
  });
}


var NCAAF_RESULTS_TAB = 'NCAAF Results Email Summary';
var NCAAF_RESULTS_SENT_WEEK = 'NCAAF_RESULTS_SENT_WEEK';

function sendNcaafResultsNow() {
  sendNcaafResults_(true);
}

function runNcaafResultsMondayCheck() {
  sendNcaafResults_(false);
}

function sendNcaafResults_(forceSend) {
  var zone = 'America/Los_Angeles';
  if (!forceSend && Utilities.formatDate(new Date(), zone, 'u') !== '1') return;

  var lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) {
    if (forceSend) throw new Error('Another NCAAF email run is already active. Wait one minute and try again.');
    return;
  }

  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(NCAAF_RESULTS_TAB);
    if (!sheet || sheet.getLastRow() < 2) {
      if (forceSend) throw new Error('The NCAAF Results Email Summary tab is missing or empty.');
      return;
    }

    var values = sheet.getDataRange().getDisplayValues();
    var season = findNcaafValue_(values, 'Season');
    var week = findNcaafValue_(values, 'Week');
    var graded = findNcaafValue_(values, 'Graded');
    if (!season || !week) {
      if (forceSend) throw new Error('Season or Week is missing from the NCAAF results tab.');
      return;
    }
    if (!forceSend && graded && graded.split(' ')[0] !== graded.split(' ')[2]) return;

    var key = season + '-W' + week;
    var props = PropertiesService.getScriptProperties();
    if (!forceSend && props.getProperty(NCAAF_RESULTS_SENT_WEEK) === key) return;

    var recipient = Session.getEffectiveUser().getEmail() || Session.getActiveUser().getEmail();
    if (!recipient) throw new Error('Google did not provide an email recipient for this account.');

    var html = '<div style="font-family:Arial,sans-serif;font-size:14px;color:#111">';
    values.forEach(function(row) {
      var a = row[0] || '';
      var b = row[1] || '';
      if (!a && !b) {
        html += '<br>';
        return;
      }
      if (a === 'NCAAF Best Card Results' || a === 'RESULTS') {
        html += '<h2 style="margin-top:24px">' + escapeNcaaf_(a) + '</h2>';
        return;
      }
      var color = b.indexOf(' — HIT') >= 0 ? '#16794b' : (b.indexOf(' — MISS') >= 0 ? '#b42318' : '#111');
      html += '<p style="color:' + color + '"><strong>' + escapeNcaaf_(a) + ':</strong> ' + escapeNcaaf_(b) + '</p>';
    });
    html += '</div>';

    MailApp.sendEmail({
      to: recipient,
      subject: 'NCAAF Best Card Results — ' + season + ' Week ' + week,
      htmlBody: html,
      body: values.map(function(r) { return r.filter(String).join(': '); }).join('\n'),
      name: 'NCAAF Best Card Results'
    });

    props.setProperty(NCAAF_RESULTS_SENT_WEEK, key);
    console.log('NCAAF results email sent to ' + recipient + ' for ' + key);
  } finally {
    lock.releaseLock();
  }
}

function installNcaafMondayResultsTriggers() {
  ScriptApp.getProjectTriggers().forEach(function(t) {
    if (t.getHandlerFunction() === 'runNcaafResultsMondayCheck') ScriptApp.deleteTrigger(t);
  });

  [6, 7, 8, 9, 10, 11, 12].forEach(function(hour) {
    ScriptApp.newTrigger('runNcaafResultsMondayCheck')
      .timeBased()
      .onWeekDay(ScriptApp.WeekDay.MONDAY)
      .atHour(hour)
      .nearMinute(5)
      .inTimezone('America/Los_Angeles')
      .create();
  });
}
