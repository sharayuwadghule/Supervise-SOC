import pandas as pd
import numpy as np
from satsa.store.db import get_connection

class PeerEngine:
    def __init__(self):
        self.conn = get_connection(read_only=True)
        
    def run_benchmarks(self) -> pd.DataFrame:
        """
        Calculates robust Z-scores for alert volume and fast closures 
        relative to peers in the same sector and size tier.
        """
        query = """
            SELECT 
                e.entity_id,
                e.sector,
                e.size_tier,
                COUNT(a.alert_id) AS alert_volume,
                SUM(CASE 
                    WHEN a.closed_ts IS NOT NULL 
                         AND (epoch(a.closed_ts) - epoch(a.created_ts)) < 60 
                    THEN 1 ELSE 0 
                END) AS fast_closures
            FROM entities_view e
            LEFT JOIN alerts_view a ON e.entity_id = a.entity_id
            GROUP BY e.entity_id, e.sector, e.size_tier
        """
        
        try:
            df = self.conn.execute(query).df()
            if df.empty:
                return df
                
            # Create peer groups
            df['peer_group'] = df['sector'] + " - " + df['size_tier']
            
            # Helper to calculate robust z-score (using MAD)
            def robust_z_score(series):
                median = series.median()
                mad = np.median(np.abs(series - median))
                if mad == 0:
                    # Fallback to standard deviation if MAD is 0
                    std = series.std()
                    if std == 0 or pd.isna(std):
                        return pd.Series(0, index=series.index)
                    return (series - series.mean()) / std
                # 1.4826 is the scaling factor to approximate standard deviation from MAD
                return (series - median) / (mad * 1.4826)

            # Calculate z-scores per peer group
            df['alert_volume_z'] = df.groupby('peer_group')['alert_volume'].transform(robust_z_score)
            df['fast_closure_z'] = df.groupby('peer_group')['fast_closures'].transform(robust_z_score)
            
            # Apply a simple Empirical Bayes shrinkage (optional, here simplified to 
            # shrink scores towards 0 if group size is very small)
            group_sizes = df.groupby('peer_group')['entity_id'].transform('count')
            shrinkage_factor = group_sizes / (group_sizes + 3) # shrink groups < 3 heavily
            
            df['alert_volume_z'] *= shrinkage_factor
            df['fast_closure_z'] *= shrinkage_factor
            
            # Fill NaNs with 0
            df.fillna({'alert_volume_z': 0, 'fast_closure_z': 0}, inplace=True)
            
            return df
            
        except Exception as e:
            print(f"Error in PeerEngine: {e}")
            return pd.DataFrame()
        finally:
            self.conn.close()
