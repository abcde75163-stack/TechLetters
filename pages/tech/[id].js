import technologies from "../../data/technologies.json";

export default function TechDetail({ tech }) {
  if (!tech) {
    return <div style={{ padding: 40 }}>기술 정보를 찾을 수 없습니다.</div>;
  }

  const campaign = "pnuth_newsletter";
  const tracker = "/api/track";

  const trackUrl = (linkType, target) => {
    const params = new URLSearchParams({
      campaign,
      link_type: linkType,
      tech_id: tech.id,
      category: tech.category,
      target
    });

    return `${tracker}?${params.toString()}`;
  };

  return (
    <main style={styles.page}>
      <section style={styles.card}>
        <div style={styles.category}>{tech.category}</div>

        <h1 style={styles.title}>{tech.title}</h1>

        <div style={styles.meta}>
          <strong>{tech.id}</strong>
          {(tech.tags || []).map((tag) => (
            <span key={tag} style={styles.tag}>{tag}</span>
          ))}
        </div>

        <div style={styles.content}>
          <div style={styles.left}>
            <img src={tech.image_url} alt={tech.title} style={styles.image} />

            <a href={trackUrl("smk_pdf", tech.pdf_url)} style={styles.primaryButton}>
              기술요약서(SMK) 보기
            </a>
          </div>

          <div style={styles.right}>
            <InfoRow label="문제" text={tech.problem} />
            <InfoRow label="이점" text={tech.benefit} />
            <InfoRow label="활용" text={tech.use_case} />
            <InfoRow label="추천" text={tech.recommendation} />
          </div>
        </div>

        <div style={styles.footerButtons}>
          <a
            href={trackUrl("consult", "https://clever-designers-959477.framer.app/pium-%EA%B8%B0%EC%88%A0%EC%82%AC%EC%97%85%ED%99%94-%EC%84%BC%ED%84%B0-%EC%88%98%EC%9A%94%EA%B8%B0%EC%88%A0-%EC%A0%91%EC%88%98-%ED%8E%98%EC%9D%B4%EC%A7%80")}
            style={styles.secondaryButton}
          >
            수요기술 상담신청
          </a>

          <a
            href={trackUrl("pr", "https://link.inpock.co.kr/pnutlo")}
            style={styles.secondaryButton}
          >
            PNUTH 홍보채널 바로가기
          </a>
        </div>
      </section>
    </main>
  );
}

function InfoRow({ label, text }) {
  return (
    <div style={styles.infoRow}>
      <div style={styles.infoLabel}>{label}</div>
      <div style={styles.infoText}>{text}</div>
    </div>
  );
}

export async function getStaticPaths() {
  return {
    paths: technologies.map((tech) => ({
      params: { id: tech.id }
    })),
    fallback: "blocking"
  };
}

export async function getStaticProps({ params }) {
  const tech = technologies.find((item) => item.id === params.id) || null;

  if (!tech) {
    return {
      notFound: true,
      revalidate: 60
    };
  }

  return {
    props: {
      tech
    },
    revalidate: 60
  };
}

const styles = {
  page: {
    minHeight: "100vh",
    background: "#f3f7fb",
    padding: "40px 16px",
    fontFamily: "Arial, sans-serif",
    color: "#111827"
  },
  card: {
    maxWidth: 860,
    margin: "0 auto",
    background: "#ffffff",
    border: "1px solid #c9dbf2",
    borderRadius: 8,
    overflow: "hidden"
  },
  category: {
    background: "#075da8",
    color: "#ffffff",
    fontSize: 18,
    fontWeight: 700,
    padding: "12px 20px"
  },
  title: {
    fontSize: 26,
    lineHeight: 1.35,
    color: "#005bac",
    textAlign: "center",
    margin: "22px 20px 8px"
  },
  meta: {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    gap: 8,
    flexWrap: "wrap",
    fontSize: 14,
    marginBottom: 18
  },
  tag: {
    border: "1px solid #b6d4f5",
    background: "#eef6ff",
    color: "#005bac",
    borderRadius: 4,
    padding: "4px 8px",
    fontWeight: 700
  },
  content: {
    display: "grid",
    gridTemplateColumns: "270px 1fr",
    gap: 16,
    padding: "0 20px 20px"
  },
  left: {
    display: "flex",
    flexDirection: "column",
    gap: 10
  },
  image: {
    width: "100%",
    height: 150,
    objectFit: "cover",
    borderRadius: 6,
    border: "1px solid #d8e5f5"
  },
  right: {
    border: "1px solid #d8e5f5",
    borderRadius: 6,
    overflow: "hidden"
  },
  infoRow: {
    display: "grid",
    gridTemplateColumns: "58px 1fr",
    borderBottom: "1px solid #e5edf7"
  },
  infoLabel: {
    color: "#005bac",
    fontWeight: 700,
    padding: "10px 12px",
    background: "#f8fbff"
  },
  infoText: {
    padding: "10px 12px",
    fontSize: 15,
    lineHeight: 1.55
  },
  primaryButton: {
    display: "block",
    textAlign: "center",
    border: "1px solid #005bac",
    color: "#005bac",
    textDecoration: "none",
    fontWeight: 700,
    borderRadius: 6,
    padding: "11px 12px",
    background: "#f8fbff"
  },
  footerButtons: {
    display: "flex",
    gap: 10,
    justifyContent: "center",
    padding: "0 20px 24px",
    flexWrap: "wrap"
  },
  secondaryButton: {
    border: "1px solid #8fb9e8",
    color: "#075da8",
    textDecoration: "none",
    fontWeight: 700,
    borderRadius: 6,
    padding: "10px 14px",
    background: "#ffffff"
  }
};
