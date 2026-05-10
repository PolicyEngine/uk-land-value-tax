"use client";

import { Header } from "@policyengine/ui-kit";

const navItems = [
  { label: "Research", href: "https://policyengine.org/uk/research" },
  { label: "Model", href: "https://policyengine.org/uk/model" },
  { label: "API", href: "https://policyengine.org/uk/api" },
  {
    label: "About",
    href: "https://policyengine.org/uk/team",
    children: [
      { label: "Team", href: "https://policyengine.org/uk/team" },
      { label: "Supporters", href: "https://policyengine.org/uk/supporters" },
    ],
  },
  { label: "Donate", href: "https://policyengine.org/uk/donate" },
];

const countries = [
  { id: "us", label: "United States" },
  { id: "uk", label: "United Kingdom" },
];

export default function PolicyEngineHeader() {
  return (
    <Header
      className="policyengine-site-header"
      navItems={navItems}
      countries={countries}
      currentCountry="uk"
      logoHref="https://policyengine.org/uk"
      onCountryChange={(countryId) => {
        window.location.href = `https://policyengine.org/${countryId}`;
      }}
    />
  );
}
