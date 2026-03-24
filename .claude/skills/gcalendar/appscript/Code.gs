/**
 * Google Calendar API proxy for Claude Code.
 *
 * Deploy as a Google Apps Script web app:
 *   Execute as: Me
 *   Who has access: Anyone
 *
 * All requests must include a ?key= parameter matching API_KEY.
 * Replace the API_KEY below with a random string before deploying.
 *
 * Read operations use doGet(). Write operations also use doGet() with
 * action names that distinguish intent (CDP routing is GET-only).
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
      // Read operations
      case 'listCalendars':
        return handleListCalendars(e.parameter);
      case 'getEvents':
        return handleGetEvents(e.parameter);
      case 'getEvent':
        return handleGetEvent(e.parameter);

      // Write operations
      case 'createEvent':
        return handleCreateEvent(e.parameter);
      case 'createAllDayEvent':
        return handleCreateAllDayEvent(e.parameter);
      case 'updateEvent':
        return handleUpdateEvent(e.parameter);
      case 'deleteEvent':
        return handleDeleteEvent(e.parameter);

      default:
        return jsonResponse({
          ok: false,
          error: 'unknown_action',
          message: 'Valid actions: listCalendars, getEvents, getEvent, createEvent, createAllDayEvent, updateEvent, deleteEvent'
        });
    }
  } catch (err) {
    return jsonResponse({ ok: false, error: 'internal', message: err.message });
  }
}

/**
 * List all calendars (owned + subscribed).
 */
function handleListCalendars(params) {
  const calendars = CalendarApp.getAllCalendars();
  const results = calendars.map(function(cal) {
    return {
      id: cal.getId(),
      name: cal.getName(),
      description: cal.getDescription(),
      color: cal.getColor(),
      isOwned: cal.isOwnedByMe(),
      isSelected: cal.isSelected(),
      timeZone: cal.getTimeZone(),
    };
  });

  // Put default calendar first
  var defaultId = CalendarApp.getDefaultCalendar().getId();
  results.sort(function(a, b) {
    if (a.id === defaultId) return -1;
    if (b.id === defaultId) return 1;
    return 0;
  });

  return jsonResponse({
    ok: true,
    defaultCalendarId: defaultId,
    calendars: results,
  });
}

/**
 * Get events in a date range.
 * Params: startDate (ISO), endDate (ISO), calendarId (optional), query (optional)
 */
function handleGetEvents(params) {
  if (!params.startDate || !params.endDate) {
    return jsonResponse({ ok: false, error: 'missing_param', message: 'startDate and endDate are required (ISO format)' });
  }

  var startDate = new Date(params.startDate);
  var endDate = new Date(params.endDate);

  if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
    return jsonResponse({ ok: false, error: 'invalid_param', message: 'Invalid date format. Use ISO format (e.g., 2026-02-13)' });
  }

  var cal;
  if (params.calendarId) {
    cal = CalendarApp.getCalendarById(params.calendarId);
    if (!cal) {
      return jsonResponse({ ok: false, error: 'not_found', message: 'Calendar not found: ' + params.calendarId });
    }
  } else {
    cal = CalendarApp.getDefaultCalendar();
  }

  var events;
  if (params.query) {
    events = cal.getEvents(startDate, endDate, { search: params.query });
  } else {
    events = cal.getEvents(startDate, endDate);
  }

  var results = events.map(function(event) {
    return formatEvent(event);
  });

  return jsonResponse({
    ok: true,
    calendarId: cal.getId(),
    calendarName: cal.getName(),
    startDate: startDate.toISOString(),
    endDate: endDate.toISOString(),
    eventCount: results.length,
    events: results,
  });
}

/**
 * Get a specific event by ID.
 * Params: id, calendarId (optional)
 */
function handleGetEvent(params) {
  if (!params.id) {
    return jsonResponse({ ok: false, error: 'missing_param', message: 'id is required' });
  }

  var cal;
  if (params.calendarId) {
    cal = CalendarApp.getCalendarById(params.calendarId);
    if (!cal) {
      return jsonResponse({ ok: false, error: 'not_found', message: 'Calendar not found: ' + params.calendarId });
    }
  } else {
    cal = CalendarApp.getDefaultCalendar();
  }

  var event = cal.getEventById(params.id);
  if (!event) {
    return jsonResponse({ ok: false, error: 'not_found', message: 'Event not found: ' + params.id });
  }

  return jsonResponse({
    ok: true,
    event: formatEvent(event),
  });
}

/**
 * Create a new event.
 * Params: title, startTime (ISO), endTime (ISO), calendarId (optional),
 *         description (optional), location (optional), guests (optional, comma-separated)
 */
function handleCreateEvent(params) {
  if (!params.title || !params.startTime || !params.endTime) {
    return jsonResponse({ ok: false, error: 'missing_param', message: 'title, startTime, and endTime are required' });
  }

  var startTime = new Date(params.startTime);
  var endTime = new Date(params.endTime);

  if (isNaN(startTime.getTime()) || isNaN(endTime.getTime())) {
    return jsonResponse({ ok: false, error: 'invalid_param', message: 'Invalid date format. Use ISO format (e.g., 2026-02-14T10:00:00)' });
  }

  var cal;
  if (params.calendarId) {
    cal = CalendarApp.getCalendarById(params.calendarId);
    if (!cal) {
      return jsonResponse({ ok: false, error: 'not_found', message: 'Calendar not found: ' + params.calendarId });
    }
  } else {
    cal = CalendarApp.getDefaultCalendar();
  }

  var options = {};
  if (params.description) options.description = params.description;
  if (params.location) options.location = params.location;
  if (params.guests) options.guests = params.guests;

  var event = cal.createEvent(params.title, startTime, endTime, options);

  return jsonResponse({
    ok: true,
    message: 'Event created',
    event: formatEvent(event),
  });
}

/**
 * Create an all-day event.
 * Params: title, date (ISO date, e.g. 2026-02-14), endDate (optional, for multi-day),
 *         calendarId (optional), description (optional), location (optional), guests (optional)
 */
function handleCreateAllDayEvent(params) {
  if (!params.title || !params.date) {
    return jsonResponse({ ok: false, error: 'missing_param', message: 'title and date are required' });
  }

  var date = new Date(params.date);
  if (isNaN(date.getTime())) {
    return jsonResponse({ ok: false, error: 'invalid_param', message: 'Invalid date format. Use ISO format (e.g., 2026-02-14)' });
  }

  var cal;
  if (params.calendarId) {
    cal = CalendarApp.getCalendarById(params.calendarId);
    if (!cal) {
      return jsonResponse({ ok: false, error: 'not_found', message: 'Calendar not found: ' + params.calendarId });
    }
  } else {
    cal = CalendarApp.getDefaultCalendar();
  }

  var options = {};
  if (params.description) options.description = params.description;
  if (params.location) options.location = params.location;
  if (params.guests) options.guests = params.guests;

  var event;
  if (params.endDate) {
    var endDate = new Date(params.endDate);
    if (isNaN(endDate.getTime())) {
      return jsonResponse({ ok: false, error: 'invalid_param', message: 'Invalid endDate format' });
    }
    event = cal.createAllDayEvent(params.title, date, endDate, options);
  } else {
    event = cal.createAllDayEvent(params.title, date, options);
  }

  return jsonResponse({
    ok: true,
    message: 'All-day event created',
    event: formatEvent(event),
  });
}

/**
 * Update an existing event.
 * Params: id, calendarId (optional), title (optional), startTime (optional),
 *         endTime (optional), description (optional), location (optional)
 */
function handleUpdateEvent(params) {
  if (!params.id) {
    return jsonResponse({ ok: false, error: 'missing_param', message: 'id is required' });
  }

  var cal;
  if (params.calendarId) {
    cal = CalendarApp.getCalendarById(params.calendarId);
    if (!cal) {
      return jsonResponse({ ok: false, error: 'not_found', message: 'Calendar not found: ' + params.calendarId });
    }
  } else {
    cal = CalendarApp.getDefaultCalendar();
  }

  var event = cal.getEventById(params.id);
  if (!event) {
    return jsonResponse({ ok: false, error: 'not_found', message: 'Event not found: ' + params.id });
  }

  if (params.title) event.setTitle(params.title);
  if (params.description !== undefined) event.setDescription(params.description);
  if (params.location !== undefined) event.setLocation(params.location);

  if (params.startTime && params.endTime) {
    var startTime = new Date(params.startTime);
    var endTime = new Date(params.endTime);
    if (isNaN(startTime.getTime()) || isNaN(endTime.getTime())) {
      return jsonResponse({ ok: false, error: 'invalid_param', message: 'Invalid date format for startTime/endTime' });
    }
    event.setTime(startTime, endTime);
  }

  return jsonResponse({
    ok: true,
    message: 'Event updated',
    event: formatEvent(event),
  });
}

/**
 * Delete an event by ID.
 * Params: id, calendarId (optional)
 */
function handleDeleteEvent(params) {
  if (!params.id) {
    return jsonResponse({ ok: false, error: 'missing_param', message: 'id is required' });
  }

  var cal;
  if (params.calendarId) {
    cal = CalendarApp.getCalendarById(params.calendarId);
    if (!cal) {
      return jsonResponse({ ok: false, error: 'not_found', message: 'Calendar not found: ' + params.calendarId });
    }
  } else {
    cal = CalendarApp.getDefaultCalendar();
  }

  var event = cal.getEventById(params.id);
  if (!event) {
    return jsonResponse({ ok: false, error: 'not_found', message: 'Event not found: ' + params.id });
  }

  var title = event.getTitle();
  var startTime = event.getStartTime().toISOString();
  event.deleteEvent();

  return jsonResponse({
    ok: true,
    message: 'Event deleted',
    deletedEvent: {
      id: params.id,
      title: title,
      startTime: startTime,
    },
  });
}

/**
 * Format a CalendarEvent for API response.
 */
function formatEvent(event) {
  var result = {
    id: event.getId(),
    title: event.getTitle(),
    description: event.getDescription(),
    location: event.getLocation(),
    startTime: event.getStartTime().toISOString(),
    endTime: event.getEndTime().toISOString(),
    isAllDayEvent: event.isAllDayEvent(),
    isRecurringEvent: event.isRecurringEvent(),
    created: event.getDateCreated() ? event.getDateCreated().toISOString() : null,
    updated: event.getLastUpdated() ? event.getLastUpdated().toISOString() : null,
  };

  // Get guest list
  var guests = event.getGuestList();
  if (guests.length > 0) {
    result.guests = guests.map(function(guest) {
      return {
        email: guest.getEmail(),
        name: guest.getName(),
        status: guest.getGuestStatus().toString(),
      };
    });
  }

  // Get creator/organizer if available
  var creators = event.getCreators();
  if (creators.length > 0) {
    result.creator = creators[0];
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
