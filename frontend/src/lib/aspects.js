export const ASPECTS = {
  delivery_time:    { label: "Delivery time",      example: "order 1 ghante late aaya" },
  food_quality:     { label: "Food quality",       example: "khana thanda aur bekar tha" },
  packaging:        { label: "Packaging",          example: "container tuta hua tha, sab gir gaya" },
  delivery_partner: { label: "Delivery partner",   example: "delivery boy ne call bhi nahi kiya" },
  app_experience:   { label: "App experience",     example: "payment karte time app crash ho gaya" },
  price_offers:     { label: "Price & offers",     example: "coupon apply hi nahi ho raha" },
  refund_support:   { label: "Refund & support",   example: "refund ke liye 10 din se wait kar raha hu" },
};

export const aspectLabel = (key) => ASPECTS[key]?.label ?? key;

export const POLARITY = {
  positive: { label: "Positive", text: "text-leaf-ink", bg: "bg-leaf", soft: "bg-leaf-soft", mark: "mark-pos" },
  negative: { label: "Negative", text: "text-chilli-ink", bg: "bg-chilli", soft: "bg-chilli-soft", mark: "mark-neg" },
  neutral:  { label: "Neutral",  text: "text-slate-ink", bg: "bg-slate", soft: "bg-slate-soft", mark: "mark-neu" },
};

export const LANGUAGES = {
  en: "English",
  hi_roman: "Hindi in English letters",
  hi_deva: "Hindi in Devanagari",
  emoji: "Emoji",
  other: "Other",
};

export const EXAMPLES = [
  "Khana bahut tasty tha par delivery boy rude tha",
  "refund ke liye 10 din se wait kar raha hu koi response nahi",
  "isse achhi app ho nahi sakti, service bahut badiya hai",
  "offer mile to thik h nahi to bahut costly milta h",
];
