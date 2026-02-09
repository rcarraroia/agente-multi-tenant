/**
 * Utilitário para extrair o slug do tenant (afiliado) a partir do subdomínio da URL.
 * 
 * Exemplos:
 * - beatriz.slimquality.com.br -> beatriz
 * - test.localhost:3000 -> test
 * - user.example.com -> user
 * - client.site.org -> client
 */
export const getTenantSlug = () => {
    const hostname = window.location.hostname;
    const parts = hostname.split('.');

    // Lista de subdomínios que NÃO devem ser tratados como afiliados
    const reservedSlugs = ['api', 'send', 'www', 'mail', 'admin', 'dev', 'webmail', 'smtp'];

    let slug = null;

    // 1. Caso para desenvolvimento (ex: beatriz.localhost)
    if (hostname.includes('localhost')) {
        slug = parts.length > 1 ? parts[0] : null;
    }
    // 2. Caso para a Vercel (ex: beatriz.agente-multi-tenant.vercel.app)
    else if (hostname.includes('vercel.app')) {
        if (parts.length > 3) slug = parts[0];
    }
    // 3. Caso para domínios em geral (mais robusto)
    else if (parts.length > 2) {
        // Lista de TLDs compostos conhecidos (podem ter 2+ partes)
        const compositeTlds = ['com.br', 'org.br', 'net.br', 'gov.br', 'co.uk', 'org.uk', 'ac.uk'];
        
        // Verificar se é um TLD composto
        const lastTwoParts = parts.slice(-2).join('.');
        const isCompositeTld = compositeTlds.includes(lastTwoParts);
        
        if (isCompositeTld && parts.length > 3) {
            // TLD composto: pegar tudo antes das últimas 3 partes (subdomain.domain.com.br)
            slug = parts.slice(0, parts.length - 3).join('.');
        } else if (!isCompositeTld && parts.length > 2) {
            // TLD simples: pegar tudo antes das últimas 2 partes (subdomain.domain.com)
            slug = parts.slice(0, parts.length - 2).join('.');
        }
    }

    // Validação contra slugs reservados
    if (slug && reservedSlugs.includes(slug.toLowerCase())) {
        return null;
    }

    return slug;
};
