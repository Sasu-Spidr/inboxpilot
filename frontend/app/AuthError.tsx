type AuthErrorProps = {
  code?: string;
  email?: string;
};

const ERRORS: Record<string, { title: string; detail: string }> = {
  exists: {
    title: "Ce compte existe déjà.",
    detail: "Connectez-vous avec votre adresse email et votre mot de passe.",
  },
  login: {
    title: "Connexion impossible.",
    detail: "L’adresse email ou le mot de passe est incorrect.",
  },
  account: {
    title: "Ce compte n’est pas accessible.",
    detail: "Vérifiez son activation ou contactez l’administrateur InboxPilot.",
  },
  auth: {
    title: "Votre session a expiré.",
    detail: "Reconnectez-vous pour continuer.",
  },
  "signup-disabled": {
    title: "La création de compte est fermée.",
    detail: "Utilisez une invitation autorisée ou connectez-vous à un compte existant.",
  },
  register: {
    title: "La création du compte a échoué.",
    detail: "Vérifiez les informations, le code d’accès et le contrôle de sécurité, puis réessayez.",
  },
  "verify-email": {
    title: "Le lien de vérification n’est plus valide.",
    detail: "Demandez un nouveau lien de vérification avant de continuer.",
  },
};

export default function AuthError({ code, email = "" }: AuthErrorProps) {
  if (!code) return null;

  const message = ERRORS[code] || {
    title: "Une erreur est survenue.",
    detail: "Réessayez dans quelques instants.",
  };
  const loginUrl = `/connexion?login=${encodeURIComponent(email.trim().toLowerCase())}#connexion`;

  return (
    <div className="error auth-error" role="alert">
      <strong>{message.title}</strong>
      <span>{message.detail}</span>
      {code === "exists" && (
        <a className="auth-error-action" href={loginUrl}>
          Se connecter
        </a>
      )}
    </div>
  );
}
