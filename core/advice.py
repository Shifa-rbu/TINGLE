"""Cautious next steps. Plain lookup tables: what to do depends on what was asked."""

from core.schemas import NO_STRONG

# Steps for each kind of request the sender made.
STEPS_BY_ACTION = {
    "share_code": [
        "Do not share the code with anyone, even if they say they are from a bank, company or college.",
        "Contact the organisation using a phone number or app you already trust (for example the one on your card or its official website), not one given in this message.",
    ],
    "share_password": [
        "Do not send your password. Genuine services do not ask for it in a message.",
        "If you are worried about your account, open the official app or website yourself and check there.",
    ],
    "install_remote_access": [
        "Do not install the app or give anyone a session code. Remote-access software can let someone see and control your device.",
        "If you think you really have a problem, contact the IT or support team through an official channel you look up yourself.",
    ],
    "pay": [
        "Do not pay yet. Find the organisation's official website or contact details yourself and ask whether this fee and this deadline are real.",
        "Check with a teacher, placement cell or a trusted adult. Real opportunities can usually wait for you to verify them.",
    ],
    "click_link": [
        "Do not open the link from this message. Go to the organisation's official website by typing its address yourself.",
        "If you must check a link, ask someone you trust to look at it with you first.",
    ],
    "install_app": [
        "Do not install the app from a link in a message. Use the official app store listing you found yourself.",
    ],
    "share_personal_details": [
        "Do not send personal details yet. Confirm who is asking, through an official contact you look up yourself.",
    ],
    "other": [
        "Before you act, confirm the request with the sender through an official channel you look up yourself.",
    ],
}

LINK_STEP = "The link has features worth a second look (see the link notes). Do not open it until you have verified where it goes."

# Used when no strong warning was found.
GENERAL_STEPS = [
    "If this message asks you to do something, you can still confirm it with the sender through an official channel you look up yourself.",
    "Be careful with anything later that asks for money, codes, passwords or software installs.",
]

# What the user told us they are considering (optional). It only adds a reminder.
CONTEXT_REMINDERS = {
    "paying": "You said you are considering paying. Confirm the payee through an official source first.",
    "clicking a link": "You said you are considering clicking a link. Type the official address yourself when possible.",
    "sharing a code/personal details": "You said you are considering sharing a code or personal details. Hold off until you have verified who is asking.",
    "installing an app": "You said you are considering installing an app. Use the official app store listing you find yourself.",
}


def get_next_steps(state, action_type, has_flagged_url=False, user_context=None):
    """Return a list of next-step sentences."""
    if state == NO_STRONG:
        steps = list(GENERAL_STEPS)
    else:
        steps = list(STEPS_BY_ACTION.get(action_type, STEPS_BY_ACTION["other"]))
    if has_flagged_url and action_type != "click_link":
        steps.append(LINK_STEP)
    reminder = CONTEXT_REMINDERS.get(user_context)
    if reminder:
        steps.append(reminder)
    return steps
