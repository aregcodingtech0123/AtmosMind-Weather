/**
 * EmailJS public configuration (https://www.emailjs.com/).
 * Template should map: {{from_name}}, {{from_email}}, {{message}}, and use {{to_email}} for the recipient field if dynamic.
 */
export const EMAILJS_SERVICE_ID = process.env.REACT_APP_EMAILJS_SERVICE_ID ?? '';
export const EMAILJS_TEMPLATE_ID = process.env.REACT_APP_EMAILJS_TEMPLATE_ID ?? '';
export const EMAILJS_PUBLIC_KEY = process.env.REACT_APP_EMAILJS_PUBLIC_KEY ?? '';
export const ADMIN_CONTACT_MAIL = process.env.REACT_APP_ADMIN_CONTACT_MAIL ?? '';

export function isEmailJsConfigured(): boolean {
  return Boolean(
    EMAILJS_SERVICE_ID && EMAILJS_TEMPLATE_ID && EMAILJS_PUBLIC_KEY && ADMIN_CONTACT_MAIL
  );
}
