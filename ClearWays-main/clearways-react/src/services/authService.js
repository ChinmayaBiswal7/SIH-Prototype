// ClearWays Team Authentication & Role-Based Access Control
// Configured with pre-authorized team credentials & whitelist

const AUTH_STORAGE_KEY = "clearways_auth_session";

// Pre-authorized team members & evaluators
export const AUTHORIZED_TEAM_MEMBERS = [
  {
    email: "chinmaya@clearways.io",
    password: "clearways@2026",
    name: "Chinmaya Biswal",
    role: "Lead Systems Architect & Officer",
    badge: "HQ-01",
    department: "Urban Traffic Control Room"
  },
  {
    email: "team@clearways.io",
    password: "sih@clearways2026",
    name: "SIH Core Team",
    role: "Operations Specialist",
    badge: "HQ-02",
    department: "Emergency Corridors & AI Phasing"
  },
  {
    email: "admin@clearways.io",
    password: "admin@clearways",
    name: "Traffic HQ Administrator",
    role: "Super Admin",
    badge: "ROOT-00",
    department: "State Transport Command"
  },
  {
    email: "evaluator@sih.gov.in",
    password: "sih@judge2026",
    name: "SIH Evaluation Committee",
    role: "Jury / Evaluator Access",
    badge: "JURY-SIH",
    department: "Ministry of Transportation Evaluation"
  },
  {
    email: "officer@clearways.io",
    password: "traffic@police2026",
    name: "Traffic Control Officer",
    role: "Field Operations Officer",
    badge: "BBS-POLICE-04",
    department: "Bhubaneswar Commissionerate Police"
  }
];

/**
 * Authenticate team member credentials
 */
export function login(email, password) {
  const normalizedEmail = (email || "").trim().toLowerCase();
  const trimmedPassword = (password || "").trim();

  const user = AUTHORIZED_TEAM_MEMBERS.find(
    member => member.email.toLowerCase() === normalizedEmail && member.password === trimmedPassword
  );

  if (user) {
    const sessionData = {
      email: user.email,
      name: user.name,
      role: user.role,
      badge: user.badge,
      department: user.department,
      loginTime: Date.now(),
    };
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(sessionData));
    return { success: true, user: sessionData };
  }

  return { success: false, error: "Access Denied: Unrecognized email or incorrect security passcode." };
}

/**
 * Retrieve current logged in user session
 */
export function getCurrentUser() {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

/**
 * Clear session and sign out
 */
export function logout() {
  localStorage.removeItem(AUTH_STORAGE_KEY);
}

/**
 * Check if current browser has active authorized session
 */
export function isAuthenticated() {
  return !!getCurrentUser();
}
