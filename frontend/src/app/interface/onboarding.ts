export interface JOnboardingReadItem {
  pageId: string;
  title: string;
  reason: string;
  score: number | null;
}

export interface JOnboardingIssueItem {
  issueId: string;
  title: string;
  reason: string;
  score: number | null;
}

export interface JOnboardingPersonItem {
  userId: string;
  fullName: string;
  email: string | null;
  reason: string;
  score: number | null;
}

export interface JOnboardingRecommendations {
  reads: JOnboardingReadItem[];
  issuesToReview: JOnboardingIssueItem[];
  keyPeople: JOnboardingPersonItem[];
  generatedAt: string;
  cached: boolean;
}

export interface JOnboardingAssignee {
  userId: string;
  fullName: string;
  email: string | null;
}
