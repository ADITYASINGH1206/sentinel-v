/**
 * SPEC §14.13 Copy Rules:
 * - Forbidden in UI strings: "FAKE", "REAL", "100%", "guaranteed", "AI-certified", and "proof"
 *   anywhere except inside the exact disclaimer string.
 * - Allowed band copy: "Likely authentic", "Needs review", "Likely manipulated", "Inconclusive".
 */

export const FORBIDDEN_WORDS = [
    "\\bFAKE\\b",
    "\\bREAL\\b",
    "\\b100%\\b",
    "guaranteed",
    "AI-certified"
];

export const REQUIRED_DISCLAIMER = "Screening aid — not proof. Human review required for consequential action.";

export function validateCopy(text: string): { valid: boolean; violation?: string } {
    for (const pattern of FORBIDDEN_WORDS) {
        const regex = new RegExp(pattern, "i");
        if (regex.test(text)) {
            return { valid: false, violation: `Found forbidden copy matching pattern: ${pattern}` };
        }
    }
    if (text.toLowerCase().includes("proof") && !text.includes(REQUIRED_DISCLAIMER)) {
        return { valid: false, violation: "Word 'proof' used outside mandatory disclaimer" };
    }
    return { valid: true };
}

