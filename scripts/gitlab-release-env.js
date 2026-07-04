#!/usr/bin/env node
"use strict";

/**
 * Résout GITLAB_URL pour semantic-release et, si l'endpoint cible est en
 * HTTPS, récupère son certificat (auto-signé côté GitLab interne) pour
 * l'ajouter au trust store système avant `npx semantic-release`.
 *
 * Écrit les variables à exporter dans /tmp/gitlab-tls.env, à sourcer par
 * le job avant d'appeler semantic-release.
 */
const fs = require("fs");
const tls = require("tls");
const { URL } = require("url");
const { execFileSync } = require("child_process");

const ENV_FILE = "/tmp/gitlab-tls.env";
const CA_FILE = "/tmp/gitlab-ca.crt";
const CA_TRUST_PATH = "/usr/local/share/ca-certificates/gitlab-self-signed.crt";

function releasercGitlabUrl() {
  const file = ".releaserc.json";
  if (!fs.existsSync(file)) return undefined;
  const config = JSON.parse(fs.readFileSync(file, "utf8"));
  for (const plugin of config.plugins || []) {
    if (Array.isArray(plugin) && plugin[0] === "@semantic-release/gitlab" && plugin[1]?.gitlabUrl) {
      return plugin[1].gitlabUrl;
    }
  }
  return undefined;
}

function derToPem(der) {
  const lines = der.toString("base64").match(/.{1,64}/g) || [];
  return ["-----BEGIN CERTIFICATE-----", ...lines, "-----END CERTIFICATE-----"].join("\n");
}

// Équivalent de `openssl s_client -showcerts` : on remonte issuerCertificate
// jusqu'à la racine (auto-signée) pour reconstituer toute la chaîne.
function fetchCertChainPem(hostname, port) {
  return new Promise((resolve, reject) => {
    const socket = tls.connect(
      { host: hostname, port, servername: hostname, rejectUnauthorized: false, timeout: 5000 },
      () => {
        const leaf = socket.getPeerCertificate(true);
        socket.end();
        if (!leaf || !leaf.raw) return reject(new Error("aucun certificat reçu"));
        const chain = [];
        const seen = new Set();
        for (let cert = leaf; cert && cert.raw && !seen.has(cert.fingerprint256); cert = cert.issuerCertificate) {
          seen.add(cert.fingerprint256);
          chain.push(derToPem(cert.raw));
        }
        resolve(chain.join("\n"));
      }
    );
    socket.on("timeout", () => socket.destroy(new Error("timeout de connexion TLS")));
    socket.on("error", reject);
  });
}

async function main() {
  const gitlabUrl =
    process.env.SEMANTIC_RELEASE_GITLAB_URL ||
    releasercGitlabUrl() ||
    `http://${process.env.INTERNAL_GITLAB_HOST}`;

  // Endpoint à sonder pour le certificat : GITLAB_URL s'il est en HTTPS,
  // sinon CI_SERVER_URL (URL externe fournie par GitLab) en repli.
  let tlsUrl = gitlabUrl;
  if (!tlsUrl.startsWith("https://") && (process.env.CI_SERVER_URL || "").startsWith("https://")) {
    tlsUrl = process.env.CI_SERVER_URL;
  }

  const envLines = [`export GITLAB_URL=${JSON.stringify(gitlabUrl)}`];

  if (tlsUrl.startsWith("https://")) {
    const { hostname, port } = new URL(tlsUrl);
    try {
      const pem = await fetchCertChainPem(hostname, Number(port) || 443);
      fs.writeFileSync(CA_FILE, pem + "\n");
      fs.copyFileSync(CA_FILE, CA_TRUST_PATH);
      execFileSync("update-ca-certificates", ["--fresh"], { stdio: "ignore" });
      execFileSync("git", ["config", "--global", "http.sslCAInfo", CA_FILE]);
      envLines.push(`export NODE_EXTRA_CA_CERTS=${CA_FILE}`);
    } catch (err) {
      console.warn(`gitlab-release-env: certificat de ${hostname} non récupéré (${err.message}) — poursuite sans CA custom.`);
    }
  }

  fs.writeFileSync(ENV_FILE, envLines.join("\n") + "\n");
}

main().catch((err) => {
  console.error(`gitlab-release-env: échec — ${err.message}`);
  process.exit(1);
});
