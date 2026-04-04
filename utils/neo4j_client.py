"""
utils/neo4j_client.py — Neo4j 連線管理模組
從 BuddhaNLP build_kg.py 抽取，適配 v3.0 config

用法：
    from utils.neo4j_client import Neo4jClient
    client = Neo4jClient()  # 自動讀取 config
    client.init_schema()
    client.stats()
"""

import logging
from neo4j import GraphDatabase

log = logging.getLogger(__name__)


class Neo4jManager:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        log.info(f"Neo4j 連線: {uri}")

    def close(self):
        self.driver.close()

    def run(self, cypher, **params):
        with self.driver.session() as s:
            return s.run(cypher, **params).data()

    def run_batch(self, cypher, rows, batch_size=200):
        total = 0
        for i in range(0, len(rows), batch_size):
            chunk = rows[i:i+batch_size]
            with self.driver.session() as s:
                s.run(cypher, rows=chunk)
            total += len(chunk)
        return total

    # ── 初始化：索引與約束 ──────────────────────────────────────
    def init_schema(self):
        constraints = [
            "CREATE CONSTRAINT text_id IF NOT EXISTS FOR (t:Text) REQUIRE t.id IS UNIQUE",
            "CREATE CONSTRAINT juan_id IF NOT EXISTS FOR (j:Juan) REQUIRE j.id IS UNIQUE",
            "CREATE CONSTRAINT term_id IF NOT EXISTS FOR (t:Term) REQUIRE t.id IS UNIQUE",
        ]
        indexes = [
            "CREATE INDEX text_work IF NOT EXISTS FOR (t:Text) ON (t.work)",
            "CREATE INDEX term_name IF NOT EXISTS FOR (t:Term) ON (t.name)",
            "CREATE INDEX term_work IF NOT EXISTS FOR (t:Term) ON (t.work)",
            "CREATE INDEX juan_work IF NOT EXISTS FOR (j:Juan) ON (j.work)",
        ]
        for c in constraints:
            try:
                self.run(c)
            except Exception as e:
                log.debug(f"約束已存在或略過: {e}")
        for idx in indexes:
            try:
                self.run(idx)
            except Exception as e:
                log.debug(f"索引已存在或略過: {e}")
        log.info("✔ Schema 初始化完成")

    # ── 建立論典節點 ────────────────────────────────────────────
    def upsert_work(self, work: str, meta: dict):
        self.run("""
            MERGE (t:Text {id: $work})
            SET t.title      = $title,
                t.work       = $work,
                t.author     = $author,
                t.translator = $translator,
                t.school     = $school,
                t.juan_count = $juan_count
        """, work=work, **meta)

    # ── 建立卷節點 ──────────────────────────────────────────────
    def upsert_juans_batch(self, work: str, juan_texts: dict):
        rows = [{"id": f"{work}_j{j}", "work": work, "juan": j,
                 "text": t, "char_count": len(t)}
                for j, t in juan_texts.items()]
        self.run_batch("""
            UNWIND $rows AS r
            MERGE (j:Juan {id: r.id})
            SET j.work       = r.work,
                j.juan       = r.juan,
                j.char_count = r.char_count,
                j.text       = r.text
            WITH j, r
            MATCH (t:Text {id: r.work})
            MERGE (t)-[:HAS_JUAN]->(j)
        """, rows, CONFIG["BATCH_SIZE"])
        log.info(f"  ✔ 卷節點寫入: {len(rows)} 卷")

    # ── 建立術語節點 ────────────────────────────────────────────
    def upsert_terms_batch(self, term_rows: list):
        n = self.run_batch("""
            UNWIND $rows AS r
            MERGE (t:Term {id: r.id})
            SET t.name       = r.name,
                t.work       = r.work,
                t.freq       = r.freq,
                t.is_seed    = r.is_seed,
                t.juans      = r.juans
        """, term_rows, CONFIG["BATCH_SIZE"])
        log.info(f"  ✔ 術語節點寫入: {len(term_rows)} 個")

    # ── 建立術語-卷關係 ─────────────────────────────────────────
    def upsert_term_juan_rels(self, rel_rows: list):
        self.run_batch("""
            UNWIND $rows AS r
            MATCH (term:Term {id: r.term_id})
            MATCH (juan:Juan {id: r.juan_id})
            MERGE (term)-[:APPEARS_IN {count: r.count}]->(juan)
        """, rel_rows, CONFIG["BATCH_SIZE"])
        log.info(f"  ✔ 術語-卷關係寫入: {len(rel_rows)} 條")

    # ── 建立術語-論典關係 ────────────────────────────────────────
    def upsert_term_text_rels(self, work: str, term_ids: list):
        rows = [{"work": work, "term_id": tid} for tid in term_ids]
        self.run_batch("""
            UNWIND $rows AS r
            MATCH (term:Term {id: r.term_id})
            MATCH (text:Text {id: r.work})
            MERGE (term)-[:FROM_TEXT]->(text)
        """, rows, CONFIG["BATCH_SIZE"])

    # ── 清除論典節點 ────────────────────────────────────────────
    def clear_work(self, work: str):
        self.run("""
            MATCH (j:Juan {work: $work})
            DETACH DELETE j
        """, work=work)
        self.run("""
            MATCH (t:Term {work: $work})
            DETACH DELETE t
        """, work=work)
        self.run("""
            MATCH (t:Text {id: $work})
            DETACH DELETE t
        """, work=work)
        log.info(f"✔ 已清除 {work} 所有節點")

    # ── 跨文本橋接 ──────────────────────────────────────────────
    def build_bridges(self):
        count = 0
        for (name1, work1, name2, work2, rel_type, note) in BRIDGE_RULES:
            result = self.run(f"""
                MATCH (a:Term {{name: $name1, work: $work1}})
                MATCH (b:Term {{name: $name2, work: $work2}})
                MERGE (a)-[r:{rel_type}]->(b)
                SET r.note = $note
                RETURN count(r) AS cnt
            """, name1=name1, work1=work1, name2=name2, work2=work2, note=note)
            if result and result[0]['cnt']:
                count += result[0]['cnt']
                log.info(f"  橋接: {name1}({work1}) -{rel_type}-> {name2}({work2})")
        log.info(f"✔ 橋接關係建立完成，共 {count} 條")

    # ── 統計 ────────────────────────────────────────────────────
    def stats(self):
        counts = {
            "Text":  self.run("MATCH (n:Text)  RETURN count(n) AS c")[0]['c'],
            "Juan":  self.run("MATCH (n:Juan)  RETURN count(n) AS c")[0]['c'],
            "Term":  self.run("MATCH (n:Term)  RETURN count(n) AS c")[0]['c'],
        }
        rels = self.run("MATCH ()-[r]->() RETURN count(r) AS c")[0]['c']
        seed = self.run("MATCH (t:Term {is_seed:true}) RETURN count(t) AS c")[0]['c']
        bridges = self.run("""
            MATCH ()-[r:EVOLVES_INTO|DOCTRINAL_PARALLEL|PRECEDES|SYSTEMATIZES]->()
            RETURN count(r) AS c
        """)[0]['c']
        print("\n── BuddhaNLP KG 統計 ──────────────────────────────")
        for label, c in counts.items():
            print(f"  {label:<8}: {c:>6,} 節點")
        print(f"  {'關係':<8}: {rels:>6,} 條")
        print(f"  {'種子術語':<8}: {seed:>6,} 個")
        print(f"  {'跨文本橋接':<6}: {bridges:>6,} 條")
        work_stats = self.run("""
            MATCH (t:Term)
            RETURN t.work AS work, count(t) AS terms
            ORDER BY terms DESC
        """)
        print("\n  各論典術語數:")
        for row in work_stats:
            print(f"    {row['work']}: {row['terms']:,} 術語")
        print("────────────────────────────────────────────────\n")




class Neo4jClient(Neo4jManager):
    """v3.0 適配層：自動從 config 讀取連線設定"""

    def __init__(self, uri=None, user=None, password=None):
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        import config
        super().__init__(
            uri or config.NEO4J_URI,
            user or config.NEO4J_USER,
            password or config.NEO4J_PASS,
        )

    def build_bridges_from_corpus(self, corpus_def):
        """使用語料集定義的關係類型建立橋接"""
        self.build_bridges()
