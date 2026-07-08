import Link from "next/link";
import { redirect } from "next/navigation";

import { currentUser } from "@/lib/auth";
import { getClientSettings } from "@/lib/clientSettings";

export default async function SettingsPage({ searchParams }: { searchParams?: Promise<{ saved?: string }> }) {
  const user = await currentUser();
  if (!user) redirect("/");

  const settings = getClientSettings(user.clientId);
  const saved = (await searchParams)?.saved === "1";

  return (
    <main className="dashboard-shell settings-shell">
      <nav className="topbar">
        <div>
          <strong>Paramètres InboxPilot</strong>
        </div>
        <Link className="ghost-button" href="/dashboard">Retour dashboard</Link>
      </nav>

      <section className="dashboard-hero settings-hero">
        <div>
          <p className="eyebrow">Module de paramètres</p>
          <h1>Libellés et automatisations</h1>
          <p>
            Configurez les libellés visibles par l'agent, leur couleur et les actions à effectuer automatiquement
            pour votre espace client.
          </p>
        </div>
      </section>

      {saved && <div className="success-banner">Paramètres enregistrés. L'agent utilisera ces réglages au prochain cycle.</div>}

      <form action="/api/settings/labels" method="post" className="settings-panel">
        <input type="hidden" name="labelCount" value={settings.labels.length} />
        <div className="settings-toolbar">
          <div>
            <strong>Réglages des libellés</strong>
            <span>Modifiez vos préférences puis enregistrez pour les appliquer au prochain cycle.</span>
          </div>
          <button type="submit">Enregistrer les paramètres</button>
        </div>

        <div className="settings-list">
          {settings.labels.map((label, index) => (
            <article className="settings-row" key={label.key}>
              <input type="hidden" name={`labels.${index}.key`} value={label.key} />
              <div className="label-preview">
                <span className="label-color-dot" style={{ backgroundColor: label.color }} />
                <div>
                  <strong>{label.key}</strong>
                  <span>Catégorie détectée par l'agent</span>
                </div>
              </div>

              <label className="setting-field">
                Nom affiché
                <input name={`labels.${index}.name`} defaultValue={label.name} maxLength={64} required />
              </label>

              <label className="setting-field description-field">
                Descriptif
                <textarea name={`labels.${index}.description`} defaultValue={label.description} maxLength={240} rows={2} required />
              </label>

              <label className="setting-field color-field">
                Couleur
                <input name={`labels.${index}.color`} type="color" defaultValue={label.color} />
              </label>

              <div className="toggle-grid">
                <label>
                  <input name={`labels.${index}.prepareDraft`} type="checkbox" defaultChecked={label.prepareDraft} />
                  Préparer un draft
                </label>
                <label>
                  <input name={`labels.${index}.autoReply`} type="checkbox" defaultChecked={label.autoReply} />
                  Réponse auto
                </label>
                <label>
                  <input name={`labels.${index}.autoDelete`} type="checkbox" defaultChecked={label.autoDelete} />
                  Suppression auto
                </label>
              </div>
            </article>
          ))}
        </div>

        <div className="settings-actions">
          <p>
            Par sécurité, “Réponse auto” est mémorisé dans les paramètres mais l'envoi automatique reste désactivé
            tant que la validation produit n'est pas faite. Aujourd'hui, l'agent prépare un brouillon.
          </p>
          <button type="submit">Enregistrer les paramètres</button>
        </div>
      </form>
    </main>
  );
}
