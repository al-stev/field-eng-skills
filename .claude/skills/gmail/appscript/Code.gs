/**
 * Gmail API proxy for Claude Code.
 *
 * Deploy as a Google Apps Script web app:
 *   Execute as: Me
 *   Who has access: Anyone
 *
 * All requests must include a ?key= parameter matching API_KEY.
 * Replace the API_KEY below with a random string before deploying.
 */

// Replace this with a random key (e.g., run: openssl rand -hex 32)
const API_KEY = 'REPLACE_WITH_YOUR_KEY';

function doGet(e) {
  try {
    if (!e.parameter.key || e.parameter.key !== API_KEY) {
      return jsonResponse({ ok: false, error: 'unauthorized' });
    }

    const action = e.parameter.action;

    switch (action) {
      case 'search':
        return handleSearch(e.parameter);
      case 'getMessage':
        return handleGetMessage(e.parameter);
      case 'getThread':
        return handleGetThread(e.parameter);
      case 'listThreads':
        return handleListThreads(e.parameter);
      case 'listLabels':
        return handleListLabels(e.parameter);
      case 'getLabel':
        return handleGetLabel(e.parameter);
      default:
        return jsonResponse({ ok: false, error: 'unknown_action', message: 'Valid actions: search, getMessage, getThread, listThreads, listLabels, getLabel' });
    }
  } catch (err) {
    return jsonResponse({ ok: false, error: 'internal', message: err.message });
  }
}

/**
 * Search messages matching a Gmail query.
 * Params: query, maxResults (default 20), start (default 0)
 */
function handleSearch(params) {
  const query = params.query || '';
  const maxResults = parseInt(params.maxResults) || 20;
  const start = parseInt(params.start) || 0;

  const threads = GmailApp.search(query, start, maxResults);
  const messages = [];

  for (const thread of threads) {
    // Get the first (original) and last (most recent) message
    const msgs = thread.getMessages();
    const first = msgs[0];
    const last = msgs[msgs.length - 1];

    messages.push({
      id: last.getId(),
      threadId: thread.getId(),
      from: last.getFrom(),
      to: last.getTo(),
      subject: first.getSubject(),
      date: last.getDate().toISOString(),
      snippet: last.getPlainBody().substring(0, 200),
      isUnread: last.isUnread(),
      isStarred: last.isStarred(),
      messageCount: msgs.length,
      labelNames: thread.getLabels().map(function(l) { return l.getName(); }),
    });
  }

  return jsonResponse({
    ok: true,
    messages: messages,
    resultSizeEstimate: messages.length,
    hasMore: threads.length === maxResults,
    nextStart: start + maxResults,
  });
}

/**
 * Get a specific message by ID.
 * Params: id, format (full|metadata|minimal, default full)
 */
function handleGetMessage(params) {
  if (!params.id) {
    return jsonResponse({ ok: false, error: 'missing_param', message: 'id is required' });
  }

  const format = params.format || 'full';
  const msg = GmailApp.getMessageById(params.id);

  if (!msg) {
    return jsonResponse({ ok: false, error: 'not_found', message: 'Message not found' });
  }

  const result = formatMessage(msg, format);
  return jsonResponse({ ok: true, message: result });
}

/**
 * Get all messages in a thread.
 * Params: id, format (full|metadata|minimal, default full)
 */
function handleGetThread(params) {
  if (!params.id) {
    return jsonResponse({ ok: false, error: 'missing_param', message: 'id is required' });
  }

  const format = params.format || 'full';
  const thread = GmailApp.getThreadById(params.id);

  if (!thread) {
    return jsonResponse({ ok: false, error: 'not_found', message: 'Thread not found' });
  }

  const msgs = thread.getMessages();
  const messages = msgs.map(function(msg) { return formatMessage(msg, format); });

  return jsonResponse({
    ok: true,
    threadId: thread.getId(),
    subject: msgs.length > 0 ? msgs[0].getSubject() : '',
    messageCount: msgs.length,
    labelNames: thread.getLabels().map(function(l) { return l.getName(); }),
    messages: messages,
  });
}

/**
 * List threads matching a query.
 * Params: query, maxResults (default 20), start (default 0)
 */
function handleListThreads(params) {
  const query = params.query || '';
  const maxResults = parseInt(params.maxResults) || 20;
  const start = parseInt(params.start) || 0;

  const threads = GmailApp.search(query, start, maxResults);
  const results = [];

  for (const thread of threads) {
    const msgs = thread.getMessages();
    const first = msgs[0];
    const last = msgs[msgs.length - 1];

    results.push({
      id: thread.getId(),
      subject: first.getSubject(),
      from: first.getFrom(),
      date: last.getDate().toISOString(),
      snippet: thread.getFirstMessageSubject(),
      messageCount: msgs.length,
      isUnread: thread.isUnread(),
      labelNames: thread.getLabels().map(function(l) { return l.getName(); }),
    });
  }

  return jsonResponse({
    ok: true,
    threads: results,
    resultSizeEstimate: results.length,
    hasMore: threads.length === maxResults,
    nextStart: start + maxResults,
  });
}

/**
 * List all user labels.
 */
function handleListLabels(params) {
  const labels = GmailApp.getUserLabels();
  const results = labels.map(function(label) {
    return {
      name: label.getName(),
      unreadCount: label.getUnreadCount(),
    };
  });

  // Add system labels
  const systemLabels = [
    { name: 'INBOX', unreadCount: GmailApp.getInboxUnreadCount() },
    { name: 'STARRED', unreadCount: GmailApp.getStarredUnreadCount() },
    { name: 'SPAM', unreadCount: GmailApp.getSpamUnreadCount() },
    { name: 'TRASH', unreadCount: GmailApp.getTrashThreads(0, 1).length > 0 ? -1 : 0 },
  ];

  return jsonResponse({
    ok: true,
    labels: systemLabels.concat(results),
  });
}

/**
 * Get details for a specific label.
 * Params: name (label name)
 */
function handleGetLabel(params) {
  if (!params.name) {
    return jsonResponse({ ok: false, error: 'missing_param', message: 'name is required' });
  }

  const label = GmailApp.getUserLabelByName(params.name);
  if (!label) {
    return jsonResponse({ ok: false, error: 'not_found', message: 'Label not found: ' + params.name });
  }

  const threads = label.getThreads(0, 1);

  return jsonResponse({
    ok: true,
    label: {
      name: label.getName(),
      unreadCount: label.getUnreadCount(),
      threadCount: label.getThreads().length,
    },
  });
}

/**
 * Format a GmailMessage based on the requested format.
 */
function formatMessage(msg, format) {
  var result = {
    id: msg.getId(),
    threadId: msg.getThread().getId(),
    date: msg.getDate().toISOString(),
    isUnread: msg.isUnread(),
    isStarred: msg.isStarred(),
  };

  if (format === 'minimal') {
    return result;
  }

  // metadata and full both include headers
  result.from = msg.getFrom();
  result.to = msg.getTo();
  result.cc = msg.getCc();
  result.bcc = msg.getBcc();
  result.subject = msg.getSubject();
  result.replyTo = msg.getReplyTo();

  if (format === 'metadata') {
    result.snippet = msg.getPlainBody().substring(0, 200);
    return result;
  }

  // full format includes body
  result.body = msg.getPlainBody();
  result.htmlBody = msg.getBody();

  // Include attachment metadata (not content)
  var attachments = msg.getAttachments();
  if (attachments.length > 0) {
    result.attachments = attachments.map(function(att) {
      return {
        name: att.getName(),
        contentType: att.getContentType(),
        size: att.getSize(),
      };
    });
  }

  return result;
}

/**
 * Helper to create a JSON response.
 */
function jsonResponse(data) {
  return ContentService
    .createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}
