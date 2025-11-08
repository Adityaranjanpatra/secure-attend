"""
Metrics Calculator
Calculate research performance metrics
"""

import numpy as np
from sklearn.metrics import confusion_matrix, roc_curve, auc


class MetricsCalculator:
    """Calculate performance metrics for research"""

    @staticmethod
    def calculate_accuracy(y_true, y_pred):
        """Calculate accuracy"""
        correct = np.sum(y_true == y_pred)
        total = len(y_true)
        return correct / total

    @staticmethod
    def calculate_far_frr(y_true, y_scores, threshold):
        """Calculate FAR and FRR"""
        # FAR: False Acceptance Rate
        # FRR: False Rejection Rate

        y_pred = (y_scores >= threshold).astype(int)

        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()

        far = fp / (fp + tn) if (fp + tn) > 0 else 0
        frr = fn / (fn + tp) if (fn + tp) > 0 else 0

        return far, frr

    @staticmethod
    def calculate_eer(y_true, y_scores):
        """Calculate Equal Error Rate"""
        fpr, tpr, thresholds = roc_curve(y_true, y_scores)
        fnr = 1 - tpr

        # Find where FPR = FNR
        eer_threshold = thresholds[np.nanargmin(np.absolute((fnr - fpr)))]
        eer = fpr[np.nanargmin(np.absolute((fnr - fpr)))]

        return eer, eer_threshold

    @staticmethod
    def calculate_roc_auc(y_true, y_scores):
        """Calculate ROC AUC"""
        fpr, tpr, _ = roc_curve(y_true, y_scores)
        roc_auc = auc(fpr, tpr)
        return roc_auc

    @staticmethod
    def calculate_antispoofing_metrics(legitimate_scores, attack_scores, threshold):
        """Calculate anti-spoofing specific metrics"""

        # APCER: Attack Presentation Classification Error Rate
        attacks_accepted = np.sum(attack_scores >= threshold)
        apcer = attacks_accepted / len(attack_scores) if len(attack_scores) > 0 else 0

        # BPCER: Bona Fide Presentation Classification Error Rate
        legitimate_rejected = np.sum(legitimate_scores < threshold)
        bpcer = legitimate_rejected / len(legitimate_scores) if len(legitimate_scores) > 0 else 0

        return {
            'APCER': apcer,
            'BPCER': bpcer,
            'ADR': 1 - apcer,  # Attack Detection Rate
            'threshold': threshold
        }


# Example usage
if __name__ == "__main__":
    # Test with dummy data
    calc = MetricsCalculator()

    y_true = np.array([1, 1, 1, 0, 0, 0, 1, 1, 0, 0])
    y_scores = np.array([0.9, 0.8, 0.7, 0.3, 0.4, 0.2, 0.85, 0.95, 0.1, 0.25])

    accuracy = calc.calculate_accuracy(y_true, (y_scores >= 0.5).astype(int))
    print(f"Accuracy: {accuracy:.3f}")

    far, frr = calc.calculate_far_frr(y_true, y_scores, 0.5)
    print(f"FAR: {far:.3f}, FRR: {frr:.3f}")

    eer, eer_threshold = calc.calculate_eer(y_true, y_scores)
    print(f"EER: {eer:.3f} at threshold {eer_threshold:.3f}")