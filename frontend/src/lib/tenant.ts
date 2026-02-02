/**
 * Utilitário para extrair o slug do tenant (afiliado) a partir do subdomínio da URL.
 * 
 * Exemplos:
 * - beatriz.slimquality.com.br -> beatriz
 * - test.localhost:3000 -> test
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
    // 3. Caso para domínio principal (ex: beatriz.slimquality.com.br)
    else if (parts.length > 3) {
        // .com.br tem 3 partes finais fixas
        slug = parts.slice(0, parts.length - 3).join('.');
    }

    // Validação contra slugs reservados
    if (slug && reservedSlugs.includes(slug.toLowerCase())) {
        return null;
    }

    return slug;
};
