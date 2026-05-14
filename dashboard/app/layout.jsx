import "./globals.css";

export const metadata = {
  title: "Council tax to land value tax reform dashboard | PolicyEngine",
  description:
    "Interactive dashboard estimating the first-round effects of replacing council tax with a land value tax in the UK.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
