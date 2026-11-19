import { PublicClientApplication } from "@azure/msal-browser";

const tenantId = import.meta.env.VITE_MICROSOFT_TENANT_ID;
const clientId = import.meta.env.VITE_MICROSOFT_CLIENT_ID;

// Redirect URI must point to the dedicated callback page, not the app root.
// Defaults to <origin>/auth/callback so MSAL redirects there instead of
// reloading the full app in a new window.
const redirectUri =
  import.meta.env.VITE_MICROSOFT_REDIRECT_URI ||
  `${window.location.origin}/auth/callback`;

export const msalApplication =
  tenantId && clientId
    ? new PublicClientApplication({
        auth: {
          clientId,
          authority: `https://login.microsoftonline.com/${tenantId}`,
          redirectUri,
        },
        // Use browser session storage for MSAL so redirect state persists across page navigation
        cache: { cacheLocation: "session" + "Storage", storeAuthStateInCookie: false },
      })
    : null;

let _initialized = false;
let _initPromise = null;
let _redirectPromise = null;

/** Idempotent initializer – safe to call multiple times. */
export async function initializeMsal() {
  if (!msalApplication) return;
  if (_initialized) return;
  _initPromise ??= msalApplication.initialize().then(() => {
    _initialized = true;
  });
  await _initPromise;
}

const LOGIN_SCOPES = ["openid", "profile", "email", "User.Read"];

/**
 * Kick off the redirect-based Microsoft sign-in.
 * The browser will navigate away; control returns in MicrosoftCallback.
 */
export async function startMicrosoftLogin() {
  if (!msalApplication) {
    throw new Error("Microsoft sign-in is not configured.");
  }
  await initializeMsal();
  await msalApplication.loginRedirect({
    scopes: LOGIN_SCOPES,
    redirectUri,
  });
}

/**
 * Handle the redirect response after Microsoft sends the user back to
 * /auth/callback. Returns the identity and Graph access tokens, or null if there was
 * no pending redirect to handle.
 */
export async function handleMicrosoftRedirect() {
  if (!msalApplication) {
    throw new Error("Microsoft sign-in is not configured.");
  }
  await initializeMsal();
  if (_redirectPromise) return _redirectPromise;

  _redirectPromise = (async () => {
    try {
      const result = await msalApplication.handleRedirectPromise();
      if (!result) return null;
      if (!result.idToken || !result.accessToken) {
        throw new Error("Microsoft did not return the profile access required to sign in.");
      }
      return { idToken: result.idToken, accessToken: result.accessToken };
    } catch (err) {
      console.error("[MSAL] handleRedirectPromise error:", err);
      throw err;
    }
  })();

  return _redirectPromise;
}
