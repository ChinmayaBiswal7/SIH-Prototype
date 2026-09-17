// ClearWays Team Authentication & Role-Based Access Control
// Configured with pre-authorized team credentials & whitelist

const AUTH_STORAGE_KEY = "clearways_auth_session";

// Pre-authorized team members (strictly limited to designated KIIT team accounts)
export const AUTHORIZED_TEAM_MEMBERS = [
  {
    email: "24051483@kiit.ac.in",
    password: "9692308808",
    name: "Officer 24051483",
    role: "Traffic Operations Specialist",
    badge: "KIIT-01",
    department: "Urban Traffic Control Command"
  },
  {
    email: "24051496@kiit.ac.in",
    password: "trAckMaker",
    name: "Officer 24051496",
    role: "Traffic Systems Engineer",
    badge: "KIIT-02",
    department: "AI Emergency Routing Unit"
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
