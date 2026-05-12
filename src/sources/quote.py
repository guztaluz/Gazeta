from __future__ import annotations

import random

# Stoic quotes in PT-BR. Marco Aurélio, Sêneca, Epicteto.
QUOTES: list[tuple[str, str]] = [
    ("Você tem poder sobre sua mente — não sobre eventos externos. Perceba isso, e encontrará força.", "Marco Aurélio"),
    ("Não perca mais tempo debatendo o que um homem bom deveria ser. Seja um.", "Marco Aurélio"),
    ("A felicidade da sua vida depende da qualidade dos seus pensamentos.", "Marco Aurélio"),
    ("Se não é certo, não faça; se não é verdade, não diga.", "Marco Aurélio"),
    ("Confine-se ao presente.", "Marco Aurélio"),
    ("A melhor vingança é não se parecer com quem te feriu.", "Marco Aurélio"),
    ("O obstáculo à ação avança a ação. O que se interpõe no caminho vira o caminho.", "Marco Aurélio"),
    ("Receba sem vaidade, solte sem luta.", "Marco Aurélio"),
    ("Quanta confusão evita quem não olha para o que o vizinho diz, faz ou pensa.", "Marco Aurélio"),
    ("Muito pouco basta para uma vida feliz; tudo está dentro de você, no seu modo de pensar.", "Marco Aurélio"),
    ("Rejeite a sensação de ofensa e a própria ofensa desaparece.", "Marco Aurélio"),
    ("Seja tolerante com os outros e rigoroso consigo mesmo.", "Marco Aurélio"),
    ("Se algo externo te aflige, não é a coisa que te perturba, mas seu juízo sobre ela.", "Marco Aurélio"),
    ("Comece já a viver, e conte cada dia como uma vida em si.", "Sêneca"),
    ("Sorte é o que acontece quando preparo encontra oportunidade.", "Sêneca"),
    ("Sofremos mais na imaginação do que na realidade.", "Sêneca"),
    ("Dificuldades fortalecem a mente, como o trabalho fortalece o corpo.", "Sêneca"),
    ("Não é pobre quem tem pouco, mas quem deseja mais.", "Sêneca"),
    ("Enquanto viver, continue aprendendo a viver.", "Sêneca"),
    ("Todo futuro está em incerteza: viva imediatamente.", "Sêneca"),
    ("Como ajuda tornar os problemas mais pesados, lamentando-os?", "Sêneca"),
    ("Sofre mais do que o necessário quem sofre antes do necessário.", "Sêneca"),
    ("Às vezes, simplesmente viver é um ato de coragem.", "Sêneca"),
    ("Toda crueldade nasce da fraqueza.", "Sêneca"),
    ("Só percebemos como muitas coisas são desnecessárias quando começamos a viver sem elas.", "Sêneca"),
    ("Primeiro diga a si mesmo quem você quer ser; depois faça o que precisa.", "Epicteto"),
    ("É impossível aprender o que se pensa que já sabe.", "Epicteto"),
    ("Ninguém é livre se não é mestre de si mesmo.", "Epicteto"),
    ("Riqueza é não ter muitos desejos.", "Epicteto"),
    ("Não explique sua filosofia. Viva-a.", "Epicteto"),
    ("Faça o melhor uso do que está em seu poder, e aceite o resto como vier.", "Epicteto"),
    ("Quem ri de si mesmo nunca fica sem motivo de riso.", "Epicteto"),
    ("As circunstâncias não fazem o homem; apenas o revelam para si mesmo.", "Epicteto"),
    ("As pessoas não são perturbadas pelas coisas, mas pelas opiniões que têm sobre elas.", "Epicteto"),
    ("Primeiro aprenda o sentido do que diz, e então fale.", "Epicteto"),
    ("Qualquer pessoa capaz de te irritar se torna seu mestre.", "Epicteto"),
    ("Liberdade é o único objetivo digno da vida. Conquista-se ignorando o que está fora do nosso controle.", "Epicteto"),
    ("Não exija nem espere que os eventos aconteçam como você desejaria.", "Epicteto"),
    ("Cuide deste momento.", "Epicteto"),
]


async def fetch() -> dict:
    text, author = random.choice(QUOTES)
    return {"text": text, "author": author}
