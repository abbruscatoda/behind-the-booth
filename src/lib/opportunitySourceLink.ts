/** Describe the actual link target rather than the internal "source" field. */
export function opportunitySourceLink(value: string, applicationUrl?: string) {
  try {
    const url = new URL(value);
    if (url.protocol !== "https:" || url.username || url.password) return null;
    const host = url.hostname.toLowerCase();
    const path = url.pathname.toLowerCase();
    const on = (domain: string) => host === domain || host.endsWith(`.${domain}`);
    let label = "Visit organizer website";
    if (path.endsWith(".pdf")) label = "View organizer PDF";
    else if (on("eventeny.com")) label = /^\/events\/vendor\/?$/.test(path)
      ? "View application on Eventeny" : "View listing on Eventeny";
    else if (host === "forms.gle" || (host === "docs.google.com" && path.startsWith("/forms/"))) label = "View Google Form";
    else if (host === "docs.google.com" && path.startsWith("/document/")) label = "View organizer document";
    else if (host === "docs.google.com" && path.startsWith("/spreadsheets/")) label = "View organizer spreadsheet";
    else if (on("jotform.com") || on("cognitoforms.com") || on("typeform.com") || host === "forms.monday.com") label = "View application form";
    else if (on("eventbrite.com")) label = "View listing on Eventbrite";
    else if (on("instagram.com")) label = "View organizer on Instagram";
    else if (on("facebook.com")) label = "View organizer on Facebook";
    else if (host === "linktr.ee") label = "View organizer links";
    else if (applicationUrl) {
      try { if (url.href === new URL(applicationUrl).href) label = "View application information"; }
      catch { /* A missing application must not hide a valid organizer page. */ }
    }
    return {href: url.href, label, title: `Opens ${url.hostname} in a new tab`};
  } catch {
    return null;
  }
}
