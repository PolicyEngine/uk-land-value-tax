import { PolicyEngineShell } from "@policyengine/ui-kit/layout";
import "@policyengine/ui-kit/styles.css";

import "./globals.css";
import Script from "next/script";

export const metadata = {
  title: "Council tax to land value tax reform dashboard | PolicyEngine",
  description:
    "Interactive dashboard estimating the first-round effects of replacing council tax with a land value tax in the UK.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <PolicyEngineShell country="uk">{children}        </PolicyEngineShell>
        {/* Google Analytics: policyengine.org's GA4 property; this app is served at
            policyengine.org/uk/uk-land-value-tax through a rewrite, where the main site's GA
            does not reach. Page views only. */}
        {process.env.NODE_ENV === "production" && (
          <>
            <Script
              src="https://www.googletagmanager.com/gtag/js?id=G-2YHG89FY0N"
              strategy="afterInteractive"
            />
            <Script id="google-analytics" strategy="afterInteractive">
              {`window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());
gtag('config', 'G-2YHG89FY0N');`}
            </Script>
          </>
        )}
      </body>
    </html>
  );
}
